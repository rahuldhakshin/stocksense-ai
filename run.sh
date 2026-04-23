#!/bin/bash
echo "Starting Indian Stock Market AI Platform..."
cd backend && uvicorn main:app --reload --port 8000 &
cd ../frontend && npm run dev &
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
