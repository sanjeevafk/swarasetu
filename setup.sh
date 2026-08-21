#!/bin/bash
set -e

# Change directory
cd /home/sanjeev/Downloads/hackhustle-26/swarasettu

# Backup current README
cp README.md CURRENT_README.md

# Remove tracking from the outer directory and initialize here
rm -rf /home/sanjeev/Downloads/hackhustle-26/.git
git init

# First commit files: Everything except the PRD and current README
mv OLD_README.md README.md
git add .
git reset CURRENT_README.md SwaraSetu_PRD
git commit -m "feat: initial SwaraSetu prototype"

# Second commit: Docs
mv CURRENT_README.md README.md
git add README.md SwaraSetu_PRD
git commit -m "feat(docs): enhance README and add PRD"

# Branch rename and Push
git branch -M main
git remote add origin https://github.com/voidcommit-afk/hackhustle-26_prototype.git
git push origin main -f
