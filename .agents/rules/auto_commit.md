# Auto-Commit Rule

Whenever code modifications, bug fixes, or feature updates are completed during a task turn:
1. Automatically run validation/build check (`npm run build` or relevant tests).
2. Automatically stage modified and new project files (`git add`).
3. Automatically commit with a concise semantic commit message (`feat:`, `fix:`, `refactor:`, `style:`).
4. Automatically push to the current working remote branch (e.g. `ironman`).
5. Keep the git working tree clean and report the commit hash in the response.
