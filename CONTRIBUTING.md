# Contributing to Nexus Mail

First off, thank you for considering contributing to Nexus Mail! 🎉

We are building the definitive open-source AI email assistant, emphasizing speed, privacy, and zero-data retention. It takes a community to make this vision a reality.

## 🚀 How Can I Contribute?

### 1. Reporting Bugs
Submit bugs via GitHub Issues. Please provide:
- Your OS and Node/Python versions.
- Steps to reproduce the issue.
- What you expected to happen vs what actually happened.
- Screenshots if applicable.

### 2. Suggesting Enhancements
Want a new integration? (e.g. Outlook/Microsoft Graph)? Have an idea for a better LLM prompt? 
- Check the issues board to ensure it hasn't already been suggested.
- Open an enhancement issue detailing the exact problem and your proposed solution.

### 3. Pull Requests
We welcome all PRs—big or small!
1. **Fork** the repo and create your branch from `main`.
2. **Setup Locally**: Ensure you have run both the React frontend and FastAPI backend successfully.
3. If you've added code that should be tested, add tests.
4. **Code Structure**: Nexus Mail heavily relies on strict Python typing and asynchronous Python patterns (`motor` for MongoDB). Ensure your code is `async` compatible where necessary.
5. Make sure the Linter passes.
6. Issue that PR!

---

## 🏗️ Development Setup

The backend uses FastAPI and MongoDB. The frontend uses Vite + React.

### Tools Needed
- Python 3.10+
- Node.js 18+
- MongoDB 6.0+ (Local or Atlas)
- Redis

### Backend Structure
- `app/ai_worker/`: Contains the Groq/OpenAI abstraction layer, the KV payload parser, and prompt definitions.
- `app/routes/`: FastAPI dependency injection and API endpoints.
- `app/services/`: Specific logic (Auth, Gmail API sync, Database connections).

### Frontend Structure
- `src/components/`: Reusable React elements (e.g. `MailThreadCard`, `SplitInbox`, `MailSpecialistTimeline`).
- `src/pages/`: Main views (Dashboard, Settings, Login).

---

## 🎨 Styleguides

### Git Commit Messages
* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Python
* We try to follow **PEP8** guidelines.
* Please use `black` for formatting and `flake8` for linting.
* Ensure FastApi models validate cleanly with standard `pydantic`.

### React
* Use Tailwind CSS for absolutely all styling. We strongly discourage separate `.css` files unless absolutely necessary for animation keyframes not supported by tailwind utility classes.
* Embrace Glassmorphism (`backdrop-blur-xl`, `bg-white/10`, `border-white/10`).

_Thank you for helping us build a smarter, more private email workspace!_
