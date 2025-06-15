# assistant-ui-langgraph-fastapi


A demonstration project that combines LangGraph, assistant-stream, and FastAPI to create an AI agent with a modern UI. The project uses [assistant-ui](https://www.assistant-ui.com/) and Next.js.

## Overview

This project showcases:

- A LangGraph agent running on a FastAPI
- Real-time response streaming to the frontend using assistant-stream
- A modern chat UI built with assistant-ui and Next.js
- Demonstrate how to integrate external tools and APIs

## Prerequisites

- Python 3.11
- Node.js v20.18.0
- npm v10.9.2
- Yarn v1.22.22

## Project Structure

```
assistant-ui-langgraph-fastapi/
├── backend/         # FastAPI + assistant-stream + LangGraph server
└── frontend/        # Next.js + assistant-ui client
```

## Setup Instructions

### Set up environment variables

Go to `./backend` and create `.env` file. Follow the example in `.env.example`.

### Backend Setup

The backend is built using the LangChain CLI and utilizes LangGraph's `create_react_agent` for agent creation.

```bash
cd backend
poetry install
poetry run python -m app.server
```

### Frontend Setup

The frontend is generated using the assistant-ui CLI tool.

```bash
cd frontend
yarn install
yarn dev
```

## Credits

Based on https://github.com/hminle/langserve-assistant-ui


## cài redisvl
https://redis.io/docs/latest/integrate/redisvl/install/
## cài redi stack trên máy thay docker
https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/homebrew/

redis-cli INFO MODULES
brew reinstall redis-stack
redis-stack-server   




 1. CÀI ĐẶT BAN ĐẦU
⚙️ Cài Python + Poetry (nếu chưa có)
bash
Copy
Edit
brew install python@3.11
brew install poetry
⚙️ Cài Node.js và pnpm (nên dùng nvm)
bash
Copy
Edit
brew install nvm
mkdir ~/.nvm
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.zprofile
echo '[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"' >> ~/.zprofile
source ~/.zprofile

nvm install 20.18.0
nvm use 20.18.0
⚙️ Cài pnpm thủ công (tránh lỗi corepack)
bash
Copy
Edit
rm -f ~/.nvm/versions/node/v20.18.0/bin/pnpm
rm -f ~/.nvm/versions/node/v20.18.0/bin/pnpx
npm install -g pnpm --force




CHẠY BACKEND (FASTAPI + LangGraph)
bash
Copy
Edit
cd assistant-ui-langgraph-fastapi/backend

# Bắt buộc: tạo README.md để Poetry không báo lỗi
touch README.md

# Tạo file .env từ mẫu
cp .env.example .env
# Rồi sửa OPENAI_API_KEY=sk-... trong file .env

# Cài thư viện Python
poetry install

# Khởi động server
poetry run python -m app.server
Server chạy tại: http://localhost:8000

✅ 3. CHẠY FRONTEND (Next.js + assistant-ui)
bash
Copy
Edit
cd ../frontend

# Cài dependencies
pnpm install

# Chạy dev
pnpm dev