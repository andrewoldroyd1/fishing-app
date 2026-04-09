import fs from 'fs';
import path from 'path';

export default async function handler(req, res) {
    if (req.headers['authorization'] !== `Bearer ${process.env.CRON_SECRET}`) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    const rivers = [
        { name: "Weber River", site: "10128500", lat: 40.8, lon: -111.4, drive_from_provo: "45 min", access: "Walk-in access between Wanship and Coalville.", regulations: "Artificial flies and lures only below Rockport Dam" },
        { name: "Provo River", site: "10163000", lat: 40.4, lon: -111.5, drive_from_provo: "15 min", access: "Easy access along US-189.", regulations: "Catch and release only in some sections." },
        { name: "Logan River", site: "10109000", lat: 41.7, lon: -111.8, drive_from_provo: "1 hr 20 min", access: "Highway 89 runs alongside river.", regulations: "Check current Utah DWR regulations" },
        { name: "Green River", site: "09234500", lat: 40.9, lon: -109.4, drive_from_provo: "2 hr 45 min", access: "Little Hole National Recreation Trail.", regulations: "Artificial flies and lures only. C&R for trout." },
        { name: "Strawberry River", site: "09287000", lat: 40.1, lon: -110.8, drive_from_provo: "1 hr 15 min", access: "Forest Road 131 follows river.", regulations: "Check current Utah DWR regulations" },
        { name: "Fremont River", site: "09333500", lat: 38.3, lon: -111.6, drive_from_provo: "2 hr 30 min", access: "Capitol Reef National Park.", regulations: "National Park regulations apply." },
        { name: "Ogden River", site: "10132000", lat: 41.2, lon: -111.9, drive_from_provo: "1 hr", access: "Access along Highway 39.", regulations: "Check current Utah DWR regulations" },
    ];

    async function getRiverData(site) {
        try {
            const r = await fetch(`https://waterservices.usgs.gov/nwis/iv/?format=json&sites=${site}&parameterCd=00060,00010`);
            const data = await r.json();
            const flow = parseFloat(data.value.timeSeries[0].values[0].value[0].value);
            let trend = "Stable";
            try { const prev = parseFloat(data.value.timeSeries[0].values[0].value[1].value); trend = flow < prev ? "Falling" : flow > prev ? "Rising" : "Stable"; } catch {}
            let tempStr = "N/A", tempF = null;
            try { const tc = parseFloat(data.value.timeSeries[1].values[0].value[0].value); tempF = Math.round((tc * 9/5 + 32) * 10) / 10; tempStr = tempF + "°F"; } catch {}
            return { flow, trend, tempStr, tempF };
        } catch { return { flow: null, trend: "N/A", tempStr: "N/A", tempF: null }; }
    }

    async function getWeather(lat, lon) {
        try {
            const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=America/Denver&forecast_days=3`);
            const data = await r.json();
            return ['Today','Tomorrow','Day After'].map((day, i) => ({ day, high: data.daily.temperature_2m_max[i], low: data.daily.temperature_2m_min[i], precip: data.daily.precipitation_sum[i], wind: data.daily.windspeed_10m_max[i], rain: data.daily.precipitation_sum[i] > 0 ? `${data.daily.precipitation_sum[i]}in` : 'No rain' }));
        } catch { return []; }
    }

    async function getFlowHistory(site) {
        try {
            const r = await fetch(`https://waterservices.usgs.gov/nwis/iv/?format=json&sites=${site}&parameterCd=00060&period=P7D`);
            const data = await r.json();
            const values = data.value.timeSeries[0].values[0].value;
            const seen = new Set(), history = [];
            for (const v of values) { const date = v.dateTime.slice(0,10); if (!seen.has(date)) { seen.add(date); history.push({ date, flow: parseFloat(v.value) }); } }
            return history.slice(-7);
        } catch { return []; }
    }

    function getScore(flow, tempF, precip, wind) {
        let fs = !flow ? 0 : flow < 150 ? 2 : flow < 300 ? 5 : flow < 400 ? 4 : flow < 800 ? 3 : 1;
        let ts = 3; if (tempF) { if (tempF >= 45 && tempF <= 65) ts = 5; else if (tempF < 38 || tempF > 72) ts = 1; }
        return Math.min(Math.round((fs + ts + ((precip > 0.2 || wind > 20) ? 2 : 4)) / 3 * 2), 10);
    }

    const month = new Date().getMonth() + 1;
    const now = new Date();
    const reportTime = now.toLocaleDateString('en-US', { month:'long', day:'numeric', year:'numeric' }) + ' at ' + now.toLocaleTimeString('en-US', { hour:'numeric', minute:'2-digit', hour12:true });
    let season, flies, bestWindow;
    if ([3,4,5].includes(month)) { season="Spring"; flies=["Midges #20-26","BWOs #18-22","Sow Bugs #18-22","Caddis Emergers #16-18"]; bestWindow="10:00 AM - 3:00 PM"; }
    else if ([6,7,8].includes(month)) { season="Summer"; flies=["Caddis #14-18","PMDs #16-20","Hoppers #6-12","Yellow Sallies #14-16"]; bestWindow="Early morning or evening"; }
    else if ([9,10,11].includes(month)) { season="Fall"; flies=["Mahogany Duns #16-18","BWOs #18-22","Midges #20-26","Streamers #6-10"]; bestWindow="11:00 AM - 2:00 PM"; }
    else { season="Winter"; flies=["Midges #22-26","Sow Bugs #18-22","Zebra Midges #20-24","WD-40s #20-22"]; bestWindow="10:00 AM - 2:00 PM"; }
    const hatches = [];
    if ([2,3,4].includes(month)) hatches.push("Little Winter Stoneflies #16-18");
    if ([3,4,5,9,10,11].includes(month)) hatches.push("Blue Winged Olives #18-22");
    if ([4,5,6].includes(month)) hatches.push("Mother's Day Caddis #14-16");
    if ([6,7,8,9].includes(month)) hatches.push("Yellow Sallies #14-16");
    if ([7,8,9].includes(month)) hatches.push("Hoppers #6-10");
    if (!hatches.length) hatches.push("Midges #22-26", "Sow Bugs #18-22");

    const results = [];
    for (const river of rivers) {
        const { flow, trend, tempStr, tempF } = await getRiverData(river.site);
        const weather = await getWeather(river.lat, river.lon);
        const history = await getFlowHistory(river.site);
        const today = weather[0] || { precip: 0, wind: 0 };
        const score = getScore(flow, tempF, today.precip, today.wind);
        results.push({ name: river.name, flow, trend, trend_emoji: trend==="Falling"?"📉 Falling (good)":trend==="Rising"?"📈 Rising":"➡️ Stable", temp: tempStr, condition: !flow?"Data unavailable":flow<150?"Very Low":flow<300?"Good conditions":flow<400?"Great conditions":flow<800?"Fishable":"Too High", score, color: score>=8?"green":score>=5?"yellow":"red", verdict: score>=8?"Excellent!":score>=5?"Decent":"Skip it", lat: river.lat, lon: river.lon, weather, weather_note: today.precip>0.1?"Rain expected - BWOs may hatch well":"Dry day - look for hatches midday", access: river.access, drive_from_provo: river.drive_from_provo, regulations: river.regulations, flow_history: history });
    }
    results.sort((a,b) => b.score - a.score);

    const data = { report_time: reportTime, best_river: results[0].name, rivers: results, sunrise: "7:00 AM", sunset: "8:00 PM", best_window: bestWindow, flies, season, hatches };
    fs.writeFileSync(path.join(process.cwd(), 'data.json'), JSON.stringify(data));
    res.status(200).json({ success: true, updated: reportTime, best: results[0].name });
}
