import datetime
import urllib.request
import json
import smtplib
import math
from email.mime.text import MIMEText

# Your email credentials
EMAIL = "andrewoldroyd1@gmail.com"
APP_PASSWORD = "zotftogpmzensefu"

# --- RIVER DEFINITIONS ---
rivers = [
    {
        "name": "Weber River",
        "site": "10128500",
        "lat": 40.8,
        "lon": -111.4,
        "access": "Walk-in access between Wanship and Coalville. Park at Wanship Bridge. Check Utah WIA program for access points.",
        "drive_from_provo": "45 min",
        "regulations": "Artificial flies and lures only below Rockport Dam"
    },
    {
        "name": "Provo River",
        "site": "10163000",
        "lat": 40.4,
        "lon": -111.5,
        "access": "Easy access along US-189. Multiple pullouts between Heber and Provo. Very accessible.",
        "drive_from_provo": "15 min",
        "regulations": "Catch and release only in some sections. Check current regs."
    },
    {
        "name": "Logan River",
        "site": "10109000",
        "lat": 41.7,
        "lon": -111.8,
        "access": "Highway 89 runs alongside river. Multiple pullouts through Logan Canyon. Very accessible.",
        "drive_from_provo": "1 hr 20 min",
        "regulations": "Check current Utah DWR regulations"
    },
    {
        "name": "Green River",
        "site": "09234500",
        "lat": 40.9,
        "lon": -109.4,
        "access": "Little Hole National Recreation Trail provides 7 miles of river access. Launch at Red Creek.",
        "drive_from_provo": "2 hr 45 min",
        "regulations": "Artificial flies and lures only. Catch and release for trout."
    },
    {
        "name": "Strawberry River",
        "site": "09287000",
        "lat": 40.1,
        "lon": -110.8,
        "access": "Access below Strawberry Reservoir. Forest Road 131 follows river. 4WD recommended.",
        "drive_from_provo": "1 hr 15 min",
        "regulations": "Check current Utah DWR regulations"
    },
    {
        "name": "Fremont River",
        "site": "09333500",
        "lat": 38.3,
        "lon": -111.6,
        "access": "Access through Capitol Reef National Park. Free entry with America the Beautiful pass.",
        "drive_from_provo": "2 hr 30 min",
        "regulations": "National Park regulations apply. Check NPS website."
    },
    {
        "name": "Ogden River",
        "site": "10132000",
        "lat": 41.2,
        "lon": -111.9,
        "access": "Pineview Reservoir to Ogden. Access along Highway 39. Urban sections easily accessible.",
        "drive_from_provo": "1 hr",
        "regulations": "Check current Utah DWR regulations"
    },
]

# --- FUNCTIONS ---
def get_river_data(site_id):
    try:
        url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd=00060,00010"
        response = urllib.request.urlopen(url, timeout=10)
        data = json.loads(response.read())
        flow = float(data["value"]["timeSeries"][0]["values"][0]["value"][0]["value"])
        try:
            prev_flow = float(data["value"]["timeSeries"][0]["values"][0]["value"][1]["value"])
            if flow < prev_flow:
                trend = "Falling"
            elif flow > prev_flow:
                trend = "Rising"
            else:
                trend = "Stable"
        except:
            trend = "Stable"
        try:
            temp_c = float(data["value"]["timeSeries"][1]["values"][0]["value"][0]["value"])
            temp_f = round((temp_c * 9/5) + 32, 1)
            temp_str = str(temp_f) + "°F"
        except:
            temp_f = None
            temp_str = "N/A"
        return flow, trend, temp_str, temp_f
    except:
        return None, "N/A", "N/A", None

def get_flow_history(site_id):
    try:
        url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd=00060&period=P7D"
        response = urllib.request.urlopen(url, timeout=10)
        data = json.loads(response.read())
        values = data["value"]["timeSeries"][0]["values"][0]["value"]
        history = []
        seen_dates = set()
        for v in values:
            date = v["dateTime"][:10]
            if date not in seen_dates:
                seen_dates.add(date)
                history.append({"date": date, "flow": float(v["value"])})
        return history[-7:]
    except:
        return []

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=America/Denver&forecast_days=3"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    days = []
    day_names = ["Today", "Tomorrow", "Day After"]
    for i in range(3):
        high = data["daily"]["temperature_2m_max"][i]
        low = data["daily"]["temperature_2m_min"][i]
        precip = data["daily"]["precipitation_sum"][i]
        wind = data["daily"]["windspeed_10m_max"][i]
        rain = f"{precip}in" if precip > 0 else "No rain"
        days.append({"day": day_names[i], "high": high, "low": low, "precip": precip, "wind": wind, "rain": rain})
    return days

def get_flow_score(flow):
    if flow is None:
        return "Data unavailable", 0
    if flow < 150:
        return "Very Low", 2
    elif flow < 300:
        return "Good conditions", 5
    elif flow < 400:
        return "Great conditions", 4
    elif flow < 800:
        return "Fishable", 3
    else:
        return "Too High", 1

def get_score(flow_score, temp_f, precip, wind):
    temp_score = 3
    if temp_f:
        if 45 <= temp_f <= 65:
            temp_score = 5
        elif 38 <= temp_f < 45 or 65 < temp_f <= 72:
            temp_score = 3
        else:
            temp_score = 1
    weather_score = 4
    if precip > 0.2 or wind > 20:
        weather_score = 2
    return min(round((flow_score + temp_score + weather_score) / 3 * 2), 10)

def get_color(score):
    if score >= 8:
        return "green"
    elif score >= 5:
        return "yellow"
    else:
        return "red"

def get_verdict(score):
    if score >= 8:
        return "Excellent!"
    elif score >= 5:
        return "Decent"
    else:
        return "Skip it"

def get_emoji(score):
    if score >= 8:
        return "🟢"
    elif score >= 5:
        return "🟡"
    else:
        return "🔴"

def get_trend_emoji(trend):
    if trend == "Falling":
        return "📉 Falling (good)"
    elif trend == "Rising":
        return "📈 Rising"
    else:
        return "➡️ Stable"

def get_hatches(month, temp_f):
    hatches = []
    if month in [2, 3, 4]:
        hatches.append("Little Winter Stoneflies #16-18")
    if month in [3, 4, 5, 9, 10, 11]:
        hatches.append("Blue Winged Olives #18-22")
    if month in [4, 5, 6]:
        hatches.append("Mother's Day Caddis #14-16")
    if month in [4, 5, 6]:
        hatches.append("March Browns #12-14")
    if month in [6, 7]:
        hatches.append("Western Green Drakes #10-12")
    if month in [6, 7, 8, 9]:
        hatches.append("Yellow Sallies #14-16")
    if month in [7, 8, 9]:
        hatches.append("Tricos #20-24")
    if month in [7, 8, 9]:
        hatches.append("Hoppers #6-10")
    if month in [9, 10]:
        hatches.append("Mahogany Duns #16-18")
    if month in [5, 6, 7, 8, 9]:
        hatches.append("PMDs #16-20")
    if temp_f and temp_f < 45:
        hatches.append("Midges #22-26 (always active in cold water)")
    return hatches if hatches else ["Midges #22-26", "Sow Bugs #18-22"]

# --- SUNRISE/SUNSET ---
def get_sunrise_sunset(lat, lon, date):
    n = date.timetuple().tm_yday
    lng_hour = lon / 15
    t_rise = n + ((6 - lng_hour) / 24)
    t_set = n + ((18 - lng_hour) / 24)
    def calc(t):
        M = (0.9856 * t) - 3.289
        L = M + (1.916 * math.sin(math.radians(M))) + (0.020 * math.sin(math.radians(2*M))) + 282.634
        L = L % 360
        RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
        Lquad = (math.floor(L/90)) * 90
        RAquad = (math.floor(RA/90)) * 90
        RA = (RA + (Lquad - RAquad)) / 15
        sinDec = 0.39782 * math.sin(math.radians(L))
        cosDec = math.cos(math.asin(sinDec))
        cosH = (-0.01454 - (sinDec * math.sin(math.radians(lat)))) / (cosDec * math.cos(math.radians(lat)))
        return cosH, RA, lng_hour
    cosH_r, RA_r, _ = calc(t_rise)
    H_rise = 360 - math.degrees(math.acos(cosH_r))
    T_rise = (H_rise/15) + RA_r - (0.06571*t_rise) - 6.622
    UT_rise = (T_rise - lng_hour) % 24
    cosH_s, RA_s, _ = calc(t_set)
    H_set = math.degrees(math.acos(cosH_s))
    T_set = (H_set/15) + RA_s - (0.06571*t_set) - 6.622
    UT_set = (T_set - lng_hour) % 24
    local_rise = (UT_rise - 6) % 24
    local_set = (UT_set - 6) % 24
    def to_time(h):
        hour = int(h)
        minute = int((h - hour) * 60)
        return datetime.datetime(date.year, date.month, date.day, hour, minute).strftime("%I:%M %p")
    return to_time(local_rise), to_time(local_set)

sunrise, sunset = get_sunrise_sunset(40.8, -111.4, datetime.date.today())

# --- SEASON AND FLIES ---
now = datetime.datetime.now()
month = now.month
report_time = now.strftime("%B %d, %Y at %I:%M %p")

if month in [3, 4, 5]:
    season = "Spring"
    flies = ["Midges #20-26", "BWOs #18-22", "Sow Bugs #18-22", "Caddis Emergers #16-18"]
    best_window = "10:00 AM - 3:00 PM"
elif month in [6, 7, 8]:
    season = "Summer"
    flies = ["Caddis #14-18", "PMDs #16-20", "Hoppers #6-12", "Yellow Sallies #14-16"]
    best_window = "Early morning or evening"
elif month in [9, 10, 11]:
    season = "Fall"
    flies = ["Mahogany Duns #16-18", "BWOs #18-22", "Midges #20-26", "Streamers #6-10"]
    best_window = "11:00 AM - 2:00 PM"
else:
    season = "Winter"
    flies = ["Midges #22-26", "Sow Bugs #18-22", "Zebra Midges #20-24", "WD-40s #20-22"]
    best_window = "10:00 AM - 2:00 PM"

# --- FETCH ALL RIVERS ---
river_results = []
weber_temp_f = None
for river in rivers:
    flow, trend, temp_str, temp_f = get_river_data(river["site"])
    weather_days = get_weather(river["lat"], river["lon"])
    flow_history = get_flow_history(river["site"])
    today_weather = weather_days[0]
    condition, flow_score = get_flow_score(flow)
    score = get_score(flow_score, temp_f, today_weather["precip"], today_weather["wind"])
    if river["name"] == "Weber River":
        weber_temp_f = temp_f
    river_results.append({
        "name": river["name"],
        "flow": flow,
        "trend": trend,
        "trend_emoji": get_trend_emoji(trend),
        "temp": temp_str,
        "condition": condition,
        "score": score,
        "color": get_color(score),
        "emoji": get_emoji(score),
        "verdict": get_verdict(score),
        "lat": river["lat"],
        "lon": river["lon"],
        "weather": weather_days,
        "weather_note": "Rain expected - BWOs may hatch well" if today_weather["precip"] > 0.1 else "Dry day - look for hatches midday",
        "access": river["access"],
        "drive_from_provo": river["drive_from_provo"],
        "regulations": river["regulations"],
        "flow_history": flow_history
    })

river_results.sort(key=lambda x: x["score"], reverse=True)
best_river = river_results[0]

hatches = get_hatches(month, weber_temp_f)

# --- BUILD EMAIL ---
flies_text = "\n".join(["  - " + f for f in flies])
hatches_text = "\n".join(["  - " + h for h in hatches])
rivers_text = ""
for r in river_results:
    flow_str = f"{r['flow']} CFS" if r['flow'] else "No data"
    rivers_text += f"{r['emoji']} {r['name']}: {r['score']}/10 — {r['verdict']} | {flow_str} | {r['trend_emoji']}\n"

message = f"""
Utah Fishing Report
{report_time}
{'='*45}

👉 BEST RIVER TODAY: {best_river['name']} ({best_river['score']}/10)

RIVER RANKINGS
{rivers_text}
HATCHES THIS WEEK
{hatches_text}

TIMING
  Sunrise: {sunrise} | Sunset: {sunset}
  Best Window: {best_window}

FLIES TO USE ({season})
{flies_text}

{'='*45}
Tight lines! 🎣
"""

print(message)

# --- SAVE DATA.JSON ---
data = {
    "report_time": report_time,
    "best_river": best_river["name"],
    "rivers": river_results,
    "sunrise": sunrise,
    "sunset": sunset,
    "best_window": best_window,
    "flies": flies,
    "season": season,
    "hatches": hatches
}

with open("/Users/andrewoldroyd/fishing-app/data.json", "w") as f:
    json.dump(data, f)
print("data.json saved!")

# --- SEND EMAIL ---
subject = f"{best_river['emoji']} Utah Fishing - Best: {best_river['name']} {best_river['score']}/10"
msg = MIMEText(message)
msg["Subject"] = subject
msg["From"] = EMAIL
msg["To"] = EMAIL

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    print("Email sent!")