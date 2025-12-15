#!/bin/bash
set -e

# Configuration
REPO_ROOT=$(pwd)
SOURCE_SITE="software/site"
OUTPUT_DIR="docs" # GitHub Pages publishing source
VERSION_FILE="versions.json"

# 1. Get Version
if [ -f "$VERSION_FILE" ]; then
    VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['schemaversion'])")
    echo "Detected version: $VERSION"
else
    echo "Error: versions.json not found!"
    exit 1
fi

# 2. Clean & Prepare Output Directory
echo "Cleaning output directory: $OUTPUT_DIR..."
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/docs"

# 3. Copy Static Assets
# A) Nested: To support legacy absolute links like /docs/schemaorg.css
echo "Copying static assets to nested $OUTPUT_DIR/docs..."
cp -r "$SOURCE_SITE/docs/"* "$OUTPUT_DIR/docs/"

# B) Root: User requested assets also be in the root serving folder
echo "Copying static assets to root $OUTPUT_DIR..."
cp -r "$SOURCE_SITE/docs/"* "$OUTPUT_DIR/"

# 4. Handle Root Specifics
# Setup index.html
echo "Configuring root index..."
cp "$SOURCE_SITE/docs/home.html" "$OUTPUT_DIR/index.html"

# 5. Apply Prod Handlers (Manual Override from includes-prod.yaml)
# We apply these to BOTH locations to ensure consistency regardless of which path is accessed.

echo "Applying prod handlers (CSS hiding, robots, sitemap)..."

# CSS: Hide development banner
# Root
cp "$SOURCE_SITE/docs/devnotehide.css" "$OUTPUT_DIR/devnote.css"
# Nested
cp "$SOURCE_SITE/docs/devnotehide.css" "$OUTPUT_DIR/docs/devnote.css"

# Robots: Allow indexing
# Root only is usually sufficient for robots.txt, but we'll ensure the file in root is correct.
cp "$SOURCE_SITE/docs/robots.txt" "$OUTPUT_DIR/robots.txt"

# Sitemap
cp "$SOURCE_SITE/docs/sitemap.xml" "$OUTPUT_DIR/sitemap.xml"

# 6. Flatten Terms (Types and Properties)
# Handlers map /([a-z])(.*)$ -> terms/properties/\1/\1\2.html
# We flatten these into the root of the output directory.
echo "Flattening terms into root..."
if [ -d "$SOURCE_SITE/terms" ]; then
    find "$SOURCE_SITE/terms" -name "*.html" -exec cp {} "$OUTPUT_DIR/" \;
else
    echo "Warning: $SOURCE_SITE/terms directory not found. Skipping terms flattening."
fi

# 7. Handle Releases
echo "Configuring releases..."
RELEASE_SRC="$SOURCE_SITE/releases/$VERSION"
VERSION_DEST="$OUTPUT_DIR/version/$VERSION"
LATEST_DEST="$OUTPUT_DIR/version/latest"

if [ -d "$RELEASE_SRC" ]; then
    mkdir -p "$VERSION_DEST"
    mkdir -p "$LATEST_DEST"
    
    echo "Copying release $VERSION to $VERSION_DEST..."
    cp -r "$RELEASE_SRC/"* "$VERSION_DEST/"
    
    echo "Copying release $VERSION to $LATEST_DEST..."
    cp -r "$RELEASE_SRC/"* "$LATEST_DEST/"
else
    echo "Warning: Release directory for $VERSION not found at $RELEASE_SRC. Skipping release copy."
fi

# 8. GitHub Pages Configuration
echo "Adding .nojekyll..."
touch "$OUTPUT_DIR/.nojekyll"

echo "Build complete. Static site generated in '$OUTPUT_DIR'."