#!/bin/bash

# Get the name of the current directory
REPO_NAME="${PWD##*/}"

# Initialize a new git repository
git init

echo "init_git_push_github.sh" > .gitignore
echo "ssuriset-twitter-clone-961e2fdf5a9a.json" >.gitignore

# Add all files to staging
git add .

# Commit the files
git commit -m "Initial commit"

# Create a new repository on GitHub and set it as the origin
gh repo create "$REPO_NAME" --public --source=. --remote=origin --push