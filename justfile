# Build the shipped static HTML pages from assets/ + build/templates/.
# Generated files (play_dice.html, index.html, play_dice.es.html, index.es.html)
# are committed build output; this is how they're regenerated after editing a
# template or asset. See ROADMAP.md Phase 1b.

build:
    python3 build/build.py

# Rebuild and confirm the output doesn't change (catches un-rebuilt drift).
verify-build: build
    git diff --exit-code play_dice.html index.html play_dice.es.html index.es.html
