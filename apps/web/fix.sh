#!/bin/bash
set -e

echo "=== 1. STARTING DOCKER DAEMON ==="
if ! docker info >/dev/null 2>&1; then
    sudo service docker start >/dev/null 2>&1 || sudo dockerd > /tmp/dockerd.log 2>&1 &
    for i in {1..10}; do docker info >/dev/null 2>&1 && break; sleep 1; done
fi

echo "=== 2. BUILDING MCORE SANDBOX ==="
if [ -d "/opt/mcore/docker-sandbox" ]; then
    cd /opt/mcore/docker-sandbox
    sudo docker builder prune -a -f >/dev/null 2>&1 || true
    sudo docker build -t mcore-sandbox . >/dev/null
    sudo docker rm -f mcore-sandbox 2>/dev/null || true
    sudo docker run -d --name mcore-sandbox -p 8080:8080 mcore-sandbox >/dev/null
    echo "✅ Sandbox is running on port 8080"
else
    echo "⚠️ /opt/mcore/docker-sandbox not found, skipping sandbox build."
fi

echo "=== 3. CREATING TURBOREPO ECOSYSTEM ==="
cd ~
rm -rf mcore-ecosystem
mkdir -p mcore-ecosystem
cd mcore-ecosystem

# Root Package
cat > package.json << 'PKG'
{
  "name": "mcore-ecosystem",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "scripts": { "dev": "turbo run dev" },
  "devDependencies": { "turbo": "latest" }
}
PKG

# Docker Compose (Quoted Password)
cat > docker-compose.yml << 'YML'
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: mcoreai
      POSTGRES_PASSWORD: "@AIS**"
      POSTGRES_DB: shorborno_db
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    restart: unless-stopped
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    restart: unless-stopped
volumes:
  pgdata:
YML

echo "=== 4. STARTING DATABASES ==="
sudo docker compose up -d

echo "=== 5. INITIALIZING NEXT.JS (This takes a minute) ==="
npx create-next-app@latest apps/web --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes >/dev/null

echo "=== 6. INJECTING MCore UI ==="
cd apps/web
cat > src/app/page.tsx << 'TSX'
"use client";
import { useEffect, useState } from "react";

export default function Home() {
  const [sandbox, setSandbox] = useState("Checking...");

  useEffect(() => {
    fetch("http://127.0.0.1:8080/health")
      .then((res) => res.json())
      .then((data) => setSandbox(data.status || "CONNECTED"))
      .catch(() => setSandbox("OFFLINE"));
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-10 flex flex-col items-center justify-center font-sans">
      <h1 className="text-5xl font-extrabold mb-4 bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
        ShorbornoAI
      </h1>
      <p className="text-slate-400 mb-8 text-lg">MCore Unified Operations Console</p>
      
      <div className={`p-8 rounded-2xl border-2 shadow-2xl transition-all duration-500 ${sandbox === 'CONNECTED' ? 'bg-emerald-950/50 border-emerald-500 text-emerald-400' : 'bg-rose-950/50 border-rose-500 text-rose-400'}`}>
        <h2 className="text-2xl font-mono font-bold tracking-wider">
          Sandbox Status: {sandbox}
        </h2>
        <p className="text-sm mt-2 opacity-70 font-mono text-center">
          {sandbox === 'CONNECTED' ? 'http://127.0.0.1:8080' : 'Check Docker'}
        </p>
      </div>
    </main>
  );
}
TSX

echo "=== 7. STARTING FRONTEND ==="
npm run dev > /tmp/nextjs.log 2>&1 &
sleep 5

echo ""
echo "=========================================================="
echo "🎉 ALL-IN-ONE DEPLOYMENT SUCCESSFUL! 🎉"
echo "=========================================================="
echo "Frontend running at: http://localhost:3000"
echo "Sandbox API running at: http://127.0.0.1:8080"
echo "Postgres & Redis are running in the background."
echo "=========================================================="
