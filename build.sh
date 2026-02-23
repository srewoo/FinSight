#!/usr/bin/env bash
# build.sh — Build FinSight Android APK via Expo EAS or local Gradle
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$ROOT/frontend"

echo "╔══════════════════════════════════════════════╗"
echo "║     FinSight — Building Android APK      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$FRONTEND"

# ── Ensure dependencies are installed ────────────────────────────────────────
if [ ! -d "node_modules" ]; then
  echo "▶ Installing node modules..."
  yarn install --frozen-lockfile
fi

# ── Choose build method ───────────────────────────────────────────────────────
BUILD_MODE="${1:-eas}"   # Pass 'local' as first arg to use local Gradle build

if [ "$BUILD_MODE" = "local" ]; then
  # ── LOCAL BUILD (no EAS account needed) ──────────────────────────────────
  echo "▶ Build mode: LOCAL (Gradle)"
  echo ""

  # ── Pick a compatible JDK (Gradle 8.x needs 17 or 21, not 25+) ──────────────
  # Check common Zulu JDK install locations first (brew cask zulu@17 / zulu@21)
  JAVA17_ZULU="/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home"
  JAVA21_ZULU="/Library/Java/JavaVirtualMachines/zulu-21.jdk/Contents/Home"
  JAVA17_HOMEBREW="$(ls -d /opt/homebrew/Cellar/openjdk@17/*/libexec/openjdk.jdk/Contents/Home 2>/dev/null | head -1)"
  JAVA21_HOMEBREW="$(ls -d /opt/homebrew/Cellar/openjdk@21/*/libexec/openjdk.jdk/Contents/Home 2>/dev/null | head -1)"

  if [ -d "$JAVA17_ZULU" ]; then
    export JAVA_HOME="$JAVA17_ZULU"
    echo "  ✓ Using JDK 17 (Zulu): $JAVA_HOME"
  elif [ -d "$JAVA21_ZULU" ]; then
    export JAVA_HOME="$JAVA21_ZULU"
    echo "  ✓ Using JDK 21 (Zulu): $JAVA_HOME"
  elif [ -n "$JAVA17_HOMEBREW" ] && [ -d "$JAVA17_HOMEBREW" ]; then
    export JAVA_HOME="$JAVA17_HOMEBREW"
    echo "  ✓ Using JDK 17 (Homebrew): $JAVA_HOME"
  elif [ -n "$JAVA21_HOMEBREW" ] && [ -d "$JAVA21_HOMEBREW" ]; then
    export JAVA_HOME="$JAVA21_HOMEBREW"
    echo "  ✓ Using JDK 21 (Homebrew): $JAVA_HOME"
  elif command -v java &> /dev/null; then
    JAVA_VER=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d'.' -f1)
    if [ "$JAVA_VER" -gt 21 ] 2>/dev/null; then
      echo "  ✗ Java $JAVA_VER detected — Gradle 8.x requires JDK 17 or 21."
      echo "    Install with: brew install --cask zulu@17"
      echo "    (requires admin password)"
      exit 1
    fi
    echo "  ✓ Using system Java $JAVA_VER"
  else
    echo "  ✗ No Java found. Install JDK 17: brew install --cask zulu@17"
    exit 1
  fi
  export PATH="$JAVA_HOME/bin:$PATH"

  # Check Android SDK — auto-detect the standard macOS path if ANDROID_HOME not set
  if [ -z "$ANDROID_HOME" ]; then
    if [ -d "$HOME/Library/Android/sdk" ]; then
      export ANDROID_HOME="$HOME/Library/Android/sdk"
      export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
      echo "  ✓ Auto-detected ANDROID_HOME: $ANDROID_HOME"
    else
      echo "  ✗ ANDROID_HOME not set and Android SDK not found at ~/Library/Android/sdk"
      echo "    Install Android Studio: https://developer.android.com/studio"
      echo "    Then set: export ANDROID_HOME=\$HOME/Library/Android/sdk"
      exit 1
    fi
  fi

  echo "▶ Running expo prebuild (generates android/ native project)..."
  # CI=1 makes expo prebuild skip interactive prompts
  CI=1 npx expo prebuild --platform android --clean

  echo ""
  echo "▶ Building debug APK with Gradle..."
  cd android
  ./gradlew assembleDebug --no-daemon

  APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
  if [ -f "$APK_PATH" ]; then
    DEST="$ROOT/FinSight-debug.apk"
    cp "$APK_PATH" "$DEST"
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║     APK built successfully!                  ║"
    echo "╠══════════════════════════════════════════════╣"
    echo "║  Location: FinSight-debug.apk             ║"
    echo "╚══════════════════════════════════════════════╝"
  else
    echo "  ✗ APK not found at $APK_PATH"
    exit 1
  fi

else
  # ── EAS BUILD (cloud, recommended) ───────────────────────────────────────
  echo "▶ Build mode: EAS Cloud Build"
  echo ""

  # Check eas-cli is installed
  if ! command -v eas &> /dev/null; then
    echo "  Installing EAS CLI..."
    npm install -g eas-cli
  fi

  # Create eas.json if it doesn't exist
  if [ ! -f "eas.json" ]; then
    echo "  Creating eas.json with preview profile..."
    cat > eas.json << 'EAS_JSON'
{
  "cli": {
    "version": ">= 10.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "android": {
        "buildType": "apk"
      },
      "distribution": "internal"
    },
    "production": {
      "android": {
        "buildType": "app-bundle"
      }
    }
  }
}
EAS_JSON
    echo "  ✓ eas.json created"
  fi

  echo "▶ Logging in to Expo (if not already logged in)..."
  eas whoami 2>/dev/null || eas login

  echo ""
  echo "▶ Starting EAS cloud build (Android APK, preview profile)..."
  echo "  This will build in the cloud and provide a download link."
  echo ""
  eas build --platform android --profile preview --non-interactive

  echo ""
  echo "╔══════════════════════════════════════════════╗"
  echo "║   EAS Build submitted!                       ║"
  echo "║   Download your APK from:                    ║"
  echo "║   https://expo.dev/accounts/[you]/builds     ║"
  echo "╚══════════════════════════════════════════════╝"
fi
