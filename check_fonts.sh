#!/bin/bash
# Step 1: Ensure Font Availability

FONTS_DIR="fonts"
REQUIRED_FONTS=("arial.ttf" "arialbd.ttf" "ShowcardGothic.ttf" "showg.ttf")
FOUND_FONTS=()
MISSING_FONTS=()
ALT_SHOWCARD_FOUND=false

echo "Current working directory: $(pwd)"
echo "Listing files in root to confirm structure:"
ls -la

if [ -d "$FONTS_DIR" ]; then
  echo "Directory '$FONTS_DIR' already exists."
  echo "Contents of '$FONTS_DIR':"
  ls -l "$FONTS_DIR"

  # Check for specific fonts
  if [ -f "$FONTS_DIR/arial.ttf" ]; then
    FOUND_FONTS+=("arial.ttf")
  else
    MISSING_FONTS+=("arial.ttf")
  fi

  if [ -f "$FONTS_DIR/arialbd.ttf" ]; then
    FOUND_FONTS+=("arialbd.ttf")
  else
    MISSING_FONTS+=("arialbd.ttf")
  fi

  # Check for ShowcardGothic.ttf or showg.ttf
  if [ -f "$FONTS_DIR/ShowcardGothic.ttf" ]; then
    FOUND_FONTS+=("ShowcardGothic.ttf")
    ALT_SHOWCARD_FOUND=true
  elif [ -f "$FONTS_DIR/showg.ttf" ]; then
    FOUND_FONTS+=("showg.ttf (as Showcard Gothic)")
    ALT_SHOWCARD_FOUND=true
  else
    MISSING_FONTS+=("ShowcardGothic.ttf (or showg.ttf)")
  fi

else
  echo "Directory '$FONTS_DIR' does not exist. Creating it."
  mkdir "$FONTS_DIR"
  if [ $? -eq 0 ]; then
    echo "Successfully created directory '$FONTS_DIR'."
  else
    echo "Failed to create directory '$FONTS_DIR'. Please check permissions."
    # Exit if directory creation fails, as further steps depend on it.
    exit 1
  fi
  # If directory was just created, all fonts are considered missing from it
  MISSING_FONTS+=("arial.ttf" "arialbd.ttf" "ShowcardGothic.ttf (or showg.ttf)")
fi

echo "" # Newline for better readability
if [ ${#FOUND_FONTS[@]} -gt 0 ]; then
  echo "Found fonts in '$FONTS_DIR':"
  for font in "${FOUND_FONTS[@]}"; do
    echo " - $font"
  done
else
  echo "No required fonts found in '$FONTS_DIR'."
fi

if [ ${#MISSING_FONTS[@]} -gt 0 ]; then
  echo "Missing fonts in '$FONTS_DIR':"
  for font in "${MISSING_FONTS[@]}"; do
    echo " - $font"
  done
  echo "IMPORTANT: Please procure the missing font files (.ttf) and place them into the '$FONTS_DIR' directory."
  echo "For Showcard Gothic, either 'ShowcardGothic.ttf' or 'showg.ttf' is acceptable."
else
  echo "All required fonts (or alternatives) seem to be present in '$FONTS_DIR'."
fi

# Specific check for Showcard Gothic for clarity
if $ALT_SHOWCARD_FOUND; then
    echo "Showcard Gothic requirement is satisfied by one of its variants."
elif [[ " ${MISSING_FONTS[@]} " =~ " ShowcardGothic.ttf (or showg.ttf) " ]]; then
    echo "Showcard Gothic (ShowcardGothic.ttf or showg.ttf) is missing."
fi

echo ""
echo "Font availability check complete."
