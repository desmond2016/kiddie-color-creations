#!/bin/bash
# Set a simple commit message to avoid parsing issues
COMMIT_MSG="Fix: Secure admin auth and refactor backend"

# Commit the staged changes
git commit -m "$COMMIT_MSG"

# Push to the main branch of the specified repository
git push https://github.com/desmond2016/kiddie-color-creations.git main