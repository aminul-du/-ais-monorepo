import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();
const app = express();
const PORT = process.env.PORT || 4000;
const AI_URL = process.env.AI_ENGINE_URL || 'http://localhost:8000';

app.use(cors());
app.use(express.json());

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'api-core', timestamp: new Date().toISOString() });
});

// Zero-Gap: API Core routes to Python AI Engine
app.post('/api/summary/catch-up', async (req: Request, res: Response) => {
  try {
    const response = await fetch(`${AI_URL}/api/ai/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: "Summarize latest emails and notifications." })
    });
    const data = await response.json();
    res.json({ summary: data.response });
  } catch (error) {
    res.status(500).json({ error: 'AI engine unreachable' });
  }
});

app.listen(PORT, () => {
  console.log(`[api-core] Listening on http://localhost:${PORT}`);
});
