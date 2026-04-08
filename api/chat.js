export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const { system, messages } = req.body;

    try {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'gpt-4o-mini',
                max_tokens: 1024,
                messages: [
                    { role: 'system', content: system },
                    ...messages
                ]
            })
        });

        const data = await response.json();

        if (!data.choices || !data.choices[0]) {
            return res.status(500).json({ error: data.error?.message || JSON.stringify(data) });
        }

        const reply = data.choices[0].message.content;
        res.status(200).json({ content: [{ text: reply }] });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
}
