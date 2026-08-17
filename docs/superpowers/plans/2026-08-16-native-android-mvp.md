# Native Android MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a native Android client for МПГУ Расписание — screens Onboarding → Institutes → Groups → Week, reading the same JSON data-branch contract the PWA reads, with offline cache and correct week-parity + homoglyph-aware group search.

**Architecture:** Single-module `:app` (Kotlin, Compose, Material 3). Data flows: `jsDelivr CDN → Ktor → DTO → Room cache → StateFlow → Compose`. Repository chooses network-first, cache-fallback per resource. DI via Hilt. Prefs via DataStore. Later Этапы swap the remote source for our own Cloudflare Worker + D1 API without touching UI.

**Tech Stack:**
- Kotlin 2.0, JDK 17, Gradle 8.10, AGP 8.6
- minSdk 26, targetSdk 34, compileSdk 34
- Jetpack Compose (BOM 2024.09), Material 3, Compose Navigation
- Hilt 2.51 for DI
- Ktor 2.3 (CIO engine) + kotlinx.serialization 1.7
- Room 2.6, DataStore 1.1
- Testing: JUnit 4, kotlin-test, MockK 1.13, Turbine 1.1, Compose UI test

---

## Non-goals (out of scope for this plan)

- Widget (Glance) — Этап 4
- Wear OS companion — Этап 4
- FCM push notifications — Этап 4
- Teacher schedule, Exam schedule screens — Этап 4
- CalendarContract deep-integration — Этап 4
- Play Store publishing (APK-only via GitHub Releases for now) — Этап 4

## File Structure

```
android/
  build.gradle.kts                                 (root, plugins)
  settings.gradle.kts                              (module include + version catalog reference)
  gradle.properties                                (JVM args, AndroidX flags)
  gradlew, gradlew.bat, gradle/wrapper/…           (Gradle wrapper 8.10)
  gradle/libs.versions.toml                        (version catalog)
  .gitignore                                       (Android-specific)
  app/
    build.gradle.kts                               (app module — plugins, deps, android{})
    proguard-rules.pro                             (empty for MVP)
    src/main/
      AndroidManifest.xml                          (single MainActivity, INTERNET perm)
      java/ru/mpgu/rasp/
        RaspApp.kt                                 (@HiltAndroidApp)
        MainActivity.kt                            (@AndroidEntryPoint, setContent)
        ui/
          theme/
            Color.kt                               (indigo palette)
            Type.kt                                (Material 3 typography)
            Theme.kt                               (RaspTheme composable)
          nav/
            Destinations.kt                        (sealed class routes)
            RaspNavGraph.kt                        (NavHost)
          onboarding/
            OnboardingScreen.kt
            OnboardingViewModel.kt
          institutes/
            InstitutesScreen.kt
            InstitutesViewModel.kt
          groups/
            GroupsScreen.kt
            GroupsViewModel.kt
          week/
            WeekScreen.kt
            WeekViewModel.kt
            DayCard.kt                             (component)
            LessonCard.kt                          (component)
        data/
          model/
            Institute.kt                           (domain)
            Group.kt                               (domain)
            Lesson.kt                              (domain)
            WeekSchedule.kt                        (domain)
          remote/
            dto/
              IndexDto.kt                          (matches meta/index.json)
              ScheduleManifestDto.kt               (institutes/{id}/schedule.json)
              GroupScheduleDto.kt                  (institutes/{id}/groups/{name}.json)
              LessonDto.kt
            ScheduleApi.kt                         (Ktor client wrapper)
            DtoMappers.kt                          (DTO → domain)
          local/
            RaspDatabase.kt                        (Room DB, version 1)
            entity/
              InstituteEntity.kt
              GroupCacheEntity.kt
            dao/
              InstituteDao.kt
              GroupCacheDao.kt
          prefs/
            UserPrefs.kt                           (DataStore wrapper)
          repo/
            ScheduleRepository.kt                  (network+cache orchestration)
        di/
          NetworkModule.kt                         (Ktor HttpClient, json)
          DatabaseModule.kt                        (Room)
          PrefsModule.kt                           (DataStore)
        util/
          WeekParity.kt                            (ISO week → odd/even)
          TimeSlots.kt                             (time_start → slot, current-lesson)
          GroupSearch.kt                           (homoglyph normalization + search key)
      res/
        values/colors.xml
        values/strings.xml
        values/themes.xml
        drawable/ic_launcher_foreground.xml
        drawable/ic_launcher_background.xml
        mipmap-anydpi-v26/ic_launcher.xml
    src/test/java/ru/mpgu/rasp/util/
      WeekParityTest.kt
      TimeSlotsTest.kt
      GroupSearchTest.kt
    src/androidTest/java/ru/mpgu/rasp/
      (empty for MVP; Compose UI test scaffold added later)
.github/workflows/
  build-android.yml                                (assemble debug APK per push; release APK per tag)
```

**One deviation from typical Gradle Android tree:** everything lives under `android/`
so the repo root stays clean (Python scraper, PWA and Android side by side).

---

## Task 1: Gradle scaffolding

**Files:**
- Create: `android/settings.gradle.kts`
- Create: `android/build.gradle.kts`
- Create: `android/gradle.properties`
- Create: `android/gradle/libs.versions.toml`
- Create: `android/gradle/wrapper/gradle-wrapper.properties`
- Create: `android/gradlew`, `android/gradlew.bat`, `android/gradle/wrapper/gradle-wrapper.jar`
- Create: `android/.gitignore`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/proguard-rules.pro`
- Create: `android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1.1: Generate Gradle wrapper**

Run from repo root:

```bash
mkdir -p android/gradle/wrapper && cd android && \
  curl -sSL -o gradle/wrapper/gradle-wrapper.jar \
    https://raw.githubusercontent.com/gradle/gradle/v8.10.0/gradle/wrapper/gradle-wrapper.jar
```

- [ ] **Step 1.2: Write `android/gradle/wrapper/gradle-wrapper.properties`**

```properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.10-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

- [ ] **Step 1.3: Write `android/gradlew` and `android/gradlew.bat`**

Copy from the Gradle 8.10 release tag:

```bash
cd android
curl -sSL -o gradlew  https://raw.githubusercontent.com/gradle/gradle/v8.10.0/gradlew
curl -sSL -o gradlew.bat https://raw.githubusercontent.com/gradle/gradle/v8.10.0/gradlew.bat
chmod +x gradlew
```

- [ ] **Step 1.4: Write `android/gradle/libs.versions.toml`**

```toml
[versions]
agp = "8.6.0"
kotlin = "2.0.20"
ksp = "2.0.20-1.0.25"
composeBom = "2024.09.02"
hilt = "2.51.1"
hiltCompose = "1.2.0"
ktor = "2.3.12"
room = "2.6.1"
datastore = "1.1.1"
coroutines = "1.8.1"
lifecycle = "2.8.5"
navigation = "2.8.1"
kotlinxSerialization = "1.7.2"
mockk = "1.13.12"
turbine = "1.1.0"

[libraries]
androidx-core-ktx = { module = "androidx.core:core-ktx", version = "1.13.1" }
androidx-activity-compose = { module = "androidx.activity:activity-compose", version = "1.9.2" }
androidx-lifecycle-runtime = { module = "androidx.lifecycle:lifecycle-runtime-ktx", version.ref = "lifecycle" }
androidx-lifecycle-viewmodel-compose = { module = "androidx.lifecycle:lifecycle-viewmodel-compose", version.ref = "lifecycle" }
androidx-navigation-compose = { module = "androidx.navigation:navigation-compose", version.ref = "navigation" }

compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
compose-ui = { module = "androidx.compose.ui:ui" }
compose-ui-tooling = { module = "androidx.compose.ui:ui-tooling" }
compose-ui-tooling-preview = { module = "androidx.compose.ui:ui-tooling-preview" }
compose-material3 = { module = "androidx.compose.material3:material3" }
compose-foundation = { module = "androidx.compose.foundation:foundation" }
compose-material-icons = { module = "androidx.compose.material:material-icons-extended" }

hilt-android = { module = "com.google.dagger:hilt-android", version.ref = "hilt" }
hilt-compiler = { module = "com.google.dagger:hilt-android-compiler", version.ref = "hilt" }
hilt-navigation-compose = { module = "androidx.hilt:hilt-navigation-compose", version.ref = "hiltCompose" }

ktor-client-core = { module = "io.ktor:ktor-client-core", version.ref = "ktor" }
ktor-client-cio = { module = "io.ktor:ktor-client-cio", version.ref = "ktor" }
ktor-client-content-negotiation = { module = "io.ktor:ktor-client-content-negotiation", version.ref = "ktor" }
ktor-serialization-kotlinx-json = { module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }
ktor-client-logging = { module = "io.ktor:ktor-client-logging", version.ref = "ktor" }

room-runtime = { module = "androidx.room:room-runtime", version.ref = "room" }
room-ktx = { module = "androidx.room:room-ktx", version.ref = "room" }
room-compiler = { module = "androidx.room:room-compiler", version.ref = "room" }

datastore-preferences = { module = "androidx.datastore:datastore-preferences", version.ref = "datastore" }

kotlinx-coroutines-android = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-android", version.ref = "coroutines" }
kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "kotlinxSerialization" }

junit = { module = "junit:junit", version = "4.13.2" }
kotlin-test = { module = "org.jetbrains.kotlin:kotlin-test", version.ref = "kotlin" }
mockk = { module = "io.mockk:mockk", version.ref = "mockk" }
kotlinx-coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test", version.ref = "coroutines" }
turbine = { module = "app.cash.turbine:turbine", version.ref = "turbine" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
hilt = { id = "com.google.dagger.hilt.android", version.ref = "hilt" }
```

- [ ] **Step 1.5: Write `android/settings.gradle.kts`**

```kotlin
pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "mpgu-rasp"
include(":app")
```

- [ ] **Step 1.6: Write `android/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
}
```

- [ ] **Step 1.7: Write `android/gradle.properties`**

```properties
org.gradle.jvmargs=-Xmx4g -Dfile.encoding=UTF-8
org.gradle.parallel=true
org.gradle.caching=true
android.useAndroidX=true
android.nonTransitiveRClass=true
kotlin.code.style=official
ksp.incremental=true
```

- [ ] **Step 1.8: Write `android/.gitignore`**

```gitignore
.gradle/
build/
local.properties
.idea/
*.iml
captures/
.externalNativeBuild/
.cxx/
```

- [ ] **Step 1.9: Write `android/app/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

android {
    namespace = "ru.mpgu.rasp"
    compileSdk = 34

    defaultConfig {
        applicationId = "ru.mpgu.rasp"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    implementation(libs.compose.foundation)
    implementation(libs.compose.material.icons)
    debugImplementation(libs.compose.ui.tooling)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.hilt.navigation.compose)

    implementation(libs.ktor.client.core)
    implementation(libs.ktor.client.cio)
    implementation(libs.ktor.client.content.negotiation)
    implementation(libs.ktor.serialization.kotlinx.json)
    implementation(libs.ktor.client.logging)

    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)

    implementation(libs.datastore.preferences)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)

    testImplementation(libs.junit)
    testImplementation(libs.kotlin.test)
    testImplementation(libs.mockk)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.turbine)
}
```

- [ ] **Step 1.10: Write `android/app/proguard-rules.pro`**

```
# Empty for MVP; R8 default is fine because release build has isMinifyEnabled=false.
```

- [ ] **Step 1.11: Write `android/app/src/main/AndroidManifest.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:name=".RaspApp"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher"
        android:supportsRtl="true"
        android:theme="@style/Theme.Rasp">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:label="@string/app_name"
            android:theme="@style/Theme.Rasp">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

- [ ] **Step 1.12: Verify Gradle bootstraps**

```bash
cd android && ./gradlew --version
```

Expected: prints Gradle 8.10, JVM 17.

- [ ] **Step 1.13: Commit**

```bash
git add android/ && \
git commit -m "feat(android): gradle scaffolding + wrapper + version catalog"
```

---

## Task 2: Resources, theme, application, entry Activity

**Files:**
- Create: `android/app/src/main/res/values/strings.xml`
- Create: `android/app/src/main/res/values/colors.xml`
- Create: `android/app/src/main/res/values/themes.xml`
- Create: `android/app/src/main/res/drawable/ic_launcher_foreground.xml`
- Create: `android/app/src/main/res/drawable/ic_launcher_background.xml`
- Create: `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`
- Create: `android/app/src/main/java/ru/mpgu/rasp/RaspApp.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/MainActivity.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/theme/Color.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/theme/Type.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/theme/Theme.kt`

- [ ] **Step 2.1: `res/values/strings.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">МПГУ Расписание</string>
    <string name="onboarding_title">Выберите институт и группу</string>
    <string name="institutes_title">Институты</string>
    <string name="groups_title">Группы</string>
    <string name="week_title_odd">Нечётная неделя</string>
    <string name="week_title_even">Чётная неделя</string>
    <string name="search_groups_hint">Поиск по коду группы</string>
    <string name="offline_banner">Офлайн — показаны сохранённые данные</string>
    <string name="empty_day">В этот день пар нет</string>
</resources>
```

- [ ] **Step 2.2: `res/values/colors.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#3730A3</color>
</resources>
```

- [ ] **Step 2.3: `res/values/themes.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.Rasp" parent="android:Theme.Material.Light.NoActionBar" />
</resources>
```

- [ ] **Step 2.4: Launcher icons (foreground + background + adaptive)**

`res/drawable/ic_launcher_background.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:pathData="M0,0h108v108h-108z" android:fillColor="#3730A3" />
</vector>
```

`res/drawable/ic_launcher_foreground.xml` (simple «Р» monogram):

```xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <group android:translateX="30" android:translateY="20">
        <path android:fillColor="#FFFFFF"
            android:pathData="M8,10 L8,74 L18,74 L18,52 L28,52 C40,52 48,44 48,32 C48,20 40,10 28,10 Z M18,20 L28,20 C34,20 38,25 38,32 C38,39 34,42 28,42 L18,42 Z" />
    </group>
</vector>
```

`res/mipmap-anydpi-v26/ic_launcher.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
```

- [ ] **Step 2.5: `ui/theme/Color.kt`**

```kotlin
package ru.mpgu.rasp.ui.theme

import androidx.compose.ui.graphics.Color

// Indigo palette matching the PWA (Tailwind indigo)
val Indigo50 = Color(0xFFEEF2FF)
val Indigo100 = Color(0xFFE0E7FF)
val Indigo200 = Color(0xFFC7D2FE)
val Indigo400 = Color(0xFF818CF8)
val Indigo500 = Color(0xFF6366F1)
val Indigo600 = Color(0xFF4F46E5)
val Indigo700 = Color(0xFF4338CA)
val Indigo800 = Color(0xFF3730A3)
val Indigo900 = Color(0xFF312E81)

val Neutral50 = Color(0xFFFAFAFA)
val Neutral100 = Color(0xFFF5F5F5)
val Neutral800 = Color(0xFF262626)
val Neutral900 = Color(0xFF171717)
```

- [ ] **Step 2.6: `ui/theme/Type.kt`**

```kotlin
package ru.mpgu.rasp.ui.theme

import androidx.compose.material3.Typography

val AppTypography = Typography()
```

- [ ] **Step 2.7: `ui/theme/Theme.kt`**

```kotlin
package ru.mpgu.rasp.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColors = lightColorScheme(
    primary = Indigo600, onPrimary = Neutral50,
    primaryContainer = Indigo100, onPrimaryContainer = Indigo900,
    secondary = Indigo500, onSecondary = Neutral50,
    background = Neutral50, onBackground = Neutral900,
    surface = Neutral50, onSurface = Neutral900,
    surfaceVariant = Indigo50, onSurfaceVariant = Indigo900,
)

private val DarkColors = darkColorScheme(
    primary = Indigo400, onPrimary = Neutral900,
    primaryContainer = Indigo800, onPrimaryContainer = Indigo100,
    secondary = Indigo500, onSecondary = Neutral900,
    background = Neutral900, onBackground = Neutral50,
    surface = Neutral900, onSurface = Neutral50,
    surfaceVariant = Neutral800, onSurfaceVariant = Indigo200,
)

@Composable
fun RaspTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colors = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val ctx = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(ctx) else dynamicLightColorScheme(ctx)
        }
        darkTheme -> DarkColors
        else -> LightColors
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colors.primary.toArgb()
            // statusBarColor is set to `primary` (dark in light mode, dark in dark mode);
            // status-bar icons must be LIGHT on that dark bg in light mode → the flag is FALSE.
            // In dark mode `primary = Indigo400` is lighter → dark icons → TRUE.
            // The correct formula for `statusBarColor = primary` is therefore `= darkTheme`.
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = darkTheme
        }
    }

    MaterialTheme(colorScheme = colors, typography = AppTypography, content = content)
}
```

- [ ] **Step 2.8: `RaspApp.kt`**

```kotlin
package ru.mpgu.rasp

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class RaspApp : Application()
```

- [ ] **Step 2.9: `MainActivity.kt`** (temporary body — nav wired in Task 8)

```kotlin
package ru.mpgu.rasp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import dagger.hilt.android.AndroidEntryPoint
import ru.mpgu.rasp.ui.theme.RaspTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RaspTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Text("МПГУ Расписание — MVP")
                }
            }
        }
    }
}
```

- [ ] **Step 2.10: Build check**

```bash
cd android && ./gradlew :app:assembleDebug
```

Expected: BUILD SUCCESSFUL, APK at `app/build/outputs/apk/debug/app-debug.apk`.

- [ ] **Step 2.11: Commit**

```bash
git add android/app/src/main/res android/app/src/main/java && \
git commit -m "feat(android): app scaffold — Hilt Application, Compose entry, Material3 theme"
```

---

## Task 3: Utility — WeekParity (TDD)

**Rationale:** The PWA uses ISO week number: even ISO week → even week. The Android app must produce the SAME answer for the same date, otherwise data drifts. Pin it with a test using known dates.

**Files:**
- Create: `android/app/src/test/java/ru/mpgu/rasp/util/WeekParityTest.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/util/WeekParity.kt`

- [ ] **Step 3.1: Write the failing test**

```kotlin
package ru.mpgu.rasp.util

import java.time.LocalDate
import kotlin.test.Test
import kotlin.test.assertEquals

class WeekParityTest {

    @Test fun `ISO week 1 is odd`() {
        // 2026-01-01 is a Thursday, ISO week 1 of 2026
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 1, 1)))
    }

    @Test fun `ISO week 2 is even`() {
        // 2026-01-08 is Thursday of ISO week 2
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 1, 8)))
    }

    @Test fun `known monday of even week`() {
        // 2026-08-17 is Monday, ISO week 34 (even)
        assertEquals(WeekParity.EVEN, WeekParity.forDate(LocalDate.of(2026, 8, 17)))
    }

    @Test fun `known monday of odd week`() {
        // 2026-08-24 is Monday, ISO week 35 (odd)
        assertEquals(WeekParity.ODD, WeekParity.forDate(LocalDate.of(2026, 8, 24)))
    }
}
```

- [ ] **Step 3.2: Run test — must FAIL to compile**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests 'ru.mpgu.rasp.util.WeekParityTest'
```

Expected: compilation error, `WeekParity` unresolved.

- [ ] **Step 3.3: Implement**

```kotlin
package ru.mpgu.rasp.util

import java.time.LocalDate
import java.time.temporal.WeekFields

enum class WeekParity { ODD, EVEN;

    companion object {
        fun forDate(date: LocalDate): WeekParity {
            val week = date.get(WeekFields.ISO.weekOfWeekBasedYear())
            return if (week % 2 == 0) EVEN else ODD
        }
    }
}
```

- [ ] **Step 3.4: Run test — must PASS**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests 'ru.mpgu.rasp.util.WeekParityTest'
```

Expected: BUILD SUCCESSFUL, 4 tests passed.

- [ ] **Step 3.5: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/util/WeekParity.kt \
        android/app/src/test/java/ru/mpgu/rasp/util/WeekParityTest.kt && \
git commit -m "feat(android): WeekParity utility with ISO-week tests"
```

---

## Task 4: Utility — TimeSlots (TDD)

**Rationale:** Duplicates the `TIME_SLOTS` sanity from Python (`scraper/normalizer/schedule_normalizer.py:22-30`) so the Android app can compute «сейчас идёт эта пара» consistently with the server. Slot indices MUST match Python exactly — the scraper writes `slot: N` values into each Lesson JSON based on those exact start times, so any drift here is a P0 correctness bug (Android shows a different slot than PWA / than the source JSON).

**Ground truth (Python `TIME_SLOTS`, line 22):**

```python
TIME_SLOTS = {
    1: ("09:00", "10:30"),
    2: ("10:40", "12:10"),
    3: ("12:40", "14:10"),
    4: ("14:20", "15:50"),
    5: ("16:00", "17:30"),
    6: ("17:40", "19:10"),
    7: ("19:20", "20:50"),
}
```

The Kotlin map below is transcribed from this. If Python `TIME_SLOTS` changes, both must change together.

**Files:**
- Create: `android/app/src/test/java/ru/mpgu/rasp/util/TimeSlotsTest.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/util/TimeSlots.kt`

- [ ] **Step 4.1: Failing test**

```kotlin
package ru.mpgu.rasp.util

import java.time.LocalTime
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class TimeSlotsTest {

    @Test fun `slot 1 starts at 9 00`() {
        assertEquals(1, TimeSlots.slotFromStart(LocalTime.of(9, 0)))
    }

    @Test fun `slot 5 starts at 16 00`() {
        assertEquals(5, TimeSlots.slotFromStart(LocalTime.of(16, 0)))
    }

    @Test fun `unknown start returns null`() {
        assertNull(TimeSlots.slotFromStart(LocalTime.of(3, 33)))
    }

    @Test fun `15 20 is between slots and returns null`() {
        // 15:20 falls in the gap between slot 4 (14:20-15:50) and slot 5 (16:00-17:30)
        // relative to slot-START-only mapping. It IS inside slot 4's range for
        // currentLessonIndex, but slotFromStart is exact-start match only.
        assertNull(TimeSlots.slotFromStart(LocalTime.of(15, 20)))
    }

    @Test fun `current lesson is the one containing now`() {
        val lessons = listOf(
            fake("09:00", "10:30"),
            fake("10:40", "12:10"),
            fake("12:40", "14:10"),
        )
        assertEquals(1, TimeSlots.currentLessonIndex(lessons, LocalTime.of(11, 45)))
    }

    @Test fun `no current lesson between blocks`() {
        val lessons = listOf(fake("09:00", "10:30"), fake("12:40", "14:10"))
        assertNull(TimeSlots.currentLessonIndex(lessons, LocalTime.of(11, 30)))
    }

    @Test fun `all seven slot starts map to their index`() {
        // Full coverage of Python TIME_SLOTS (schedule_normalizer.py:22-30) — any
        // mistranscription of a slot start would show up here even for the slots
        // not explicitly covered by other tests.
        val expected = mapOf(
            LocalTime.of(9, 0)   to 1,
            LocalTime.of(10, 40) to 2,
            LocalTime.of(12, 40) to 3,
            LocalTime.of(14, 20) to 4,
            LocalTime.of(16, 0)  to 5,
            LocalTime.of(17, 40) to 6,
            LocalTime.of(19, 20) to 7,
        )
        for ((time, slot) in expected) {
            assertEquals(slot, TimeSlots.slotFromStart(time), "slot for $time")
        }
    }

    @Test fun `currentLessonIndex includes lesson start (inclusive lower bound)`() {
        val lessons = listOf(fake("09:00", "10:30"), fake("10:40", "12:10"))
        assertEquals(1, TimeSlots.currentLessonIndex(lessons, LocalTime.of(10, 40)))
    }

    @Test fun `currentLessonIndex excludes lesson end (exclusive upper bound)`() {
        val lessons = listOf(fake("09:00", "10:30"), fake("10:40", "12:10"))
        assertNull(TimeSlots.currentLessonIndex(lessons, LocalTime.of(10, 30)))
    }

    private fun fake(start: String, end: String) = TimeSlots.LessonTimeRange(
        start = LocalTime.parse(start),
        end = LocalTime.parse(end),
    )
}
```

- [ ] **Step 4.2: Implement**

```kotlin
package ru.mpgu.rasp.util

import java.time.LocalTime

object TimeSlots {
    // Matches TIME_SLOTS in scraper/normalizer/schedule_normalizer.py (lines 22-30).
    // Keep in sync — the scraper stamps `slot: N` based on these exact starts,
    // and Android/PWA/backend must all resolve to the same N for the same time.
    private val slotStarts = linkedMapOf(
        LocalTime.of(9, 0)   to 1,
        LocalTime.of(10, 40) to 2,
        LocalTime.of(12, 40) to 3,
        LocalTime.of(14, 20) to 4,
        LocalTime.of(16, 0)  to 5,
        LocalTime.of(17, 40) to 6,
        LocalTime.of(19, 20) to 7,
    )

    fun slotFromStart(time: LocalTime): Int? = slotStarts[time]

    data class LessonTimeRange(val start: LocalTime, val end: LocalTime)

    fun currentLessonIndex(lessons: List<LessonTimeRange>, now: LocalTime): Int? {
        lessons.forEachIndexed { i, r -> if (now >= r.start && now < r.end) return i }
        return null
    }
}
```

- [ ] **Step 4.3: Run test — PASS**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests 'ru.mpgu.rasp.util.TimeSlotsTest'
```

- [ ] **Step 4.4: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/util/TimeSlots.kt \
        android/app/src/test/java/ru/mpgu/rasp/util/TimeSlotsTest.kt && \
git commit -m "feat(android): TimeSlots utility with slot-index and current-lesson tests"
```

---

## Task 5: Utility — GroupSearch (homoglyph-aware, TDD)

**Rationale:** The PWA and both Telegram bots normalize group codes with the same homoglyph table (see `.claude/skills/handling-mpgu-group-codes/SKILL.md` and `cloudflare-worker-bot/worker.js` `HOMO`/`searchKey`). The Android search must produce the same key so a user typing `BOP40-PFK2501` (Latin) matches `ВОП40-ПФК2501` (Cyrillic).

**Files:**
- Create: `android/app/src/test/java/ru/mpgu/rasp/util/GroupSearchTest.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/util/GroupSearch.kt`

- [ ] **Step 5.1: Failing test**

The HOMO table is VISUAL homoglyphs (not phonetic transliteration). Only the
12 Latin letters that share glyphs with Cyrillic — A, B, C, E, H, K, M, O, P,
T, X, Y — fold. `F` has no shape-partner in Cyrillic Ф; `V` has no shape
partner in В; etc. Tests must exercise inputs where every folded letter
actually IS in the HOMO table.

```kotlin
package ru.mpgu.rasp.util

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class GroupSearchTest {

    @Test fun `latin lookalikes fold to cyrillic`() {
        // All five letters in "BOEHK" have Cyrillic homoglyphs
        // (B→В, O→О, E→Е, H→Н, K→К).
        assertEquals("ВОЕНК", GroupSearch.searchKey("BOEHK"))
    }

    @Test fun `whitespace and separators are stripped`() {
        // Cyrillic-only input — no folding needed, only strip+uppercase.
        assertEquals("ВОП40ПФК2501", GroupSearch.searchKey(" ВОП 40 - ПФК_2501 "))
    }

    @Test fun `lowercase is uppercased before folding`() {
        assertEquals("ВОЕНК", GroupSearch.searchKey("boehk"))
    }

    @Test fun `mixed-script query matches full cyrillic group`() {
        // Real UX: user reads "ВОП40-ПФК2501" off a poster and types the
        // homoglyph-safe prefix in Latin (BO → ВО), keeping the rest in
        // Cyrillic because П and Ф have no Latin look-alikes.
        val groups = listOf("ВОП40-ПФК2501", "ГПОФ01-ГЕО2501")
        val hits = GroupSearch.filter(groups, "BOП40")
        assertTrue("ВОП40-ПФК2501" in hits)
        assertTrue("ГПОФ01-ГЕО2501" !in hits)
    }

    @Test fun `numeric query filters`() {
        val groups = listOf("ВОП40-ПФК2501", "ГПОФ01-ГЕО2501")
        val hits = GroupSearch.filter(groups, "40")
        assertTrue("ВОП40-ПФК2501" in hits)
        assertTrue("ГПОФ01-ГЕО2501" !in hits)
    }
}
```

- [ ] **Step 5.2: Implement**

```kotlin
package ru.mpgu.rasp.util

object GroupSearch {
    // Same table as cloudflare-worker-bot/worker.js and Python scraper.
    private val HOMO = mapOf(
        'A' to 'А', 'B' to 'В', 'C' to 'С', 'E' to 'Е', 'H' to 'Н',
        'K' to 'К', 'M' to 'М', 'O' to 'О', 'P' to 'Р', 'T' to 'Т',
        'X' to 'Х', 'Y' to 'У',
    )
    private val STRIP = Regex("[\\s\\-_]")

    fun searchKey(input: String): String {
        val upper = input.trim().uppercase()
        val folded = buildString(upper.length) {
            for (c in upper) append(HOMO[c] ?: c)
        }
        return STRIP.replace(folded, "")
    }

    fun filter(groups: List<String>, query: String): List<String> {
        if (query.isBlank()) return groups
        val key = searchKey(query)
        return groups.filter { searchKey(it).contains(key) }
    }
}
```

- [ ] **Step 5.3: Run test — PASS**

```bash
cd android && ./gradlew :app:testDebugUnitTest --tests 'ru.mpgu.rasp.util.GroupSearchTest'
```

- [ ] **Step 5.4: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/util/GroupSearch.kt \
        android/app/src/test/java/ru/mpgu/rasp/util/GroupSearchTest.kt && \
git commit -m "feat(android): GroupSearch homoglyph-aware key + filter"
```

---

## Task 6: Domain models

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/model/Institute.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/model/Group.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/model/Lesson.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/model/WeekSchedule.kt`

- [ ] **Step 6.1: `Institute.kt`**

```kotlin
package ru.mpgu.rasp.data.model

data class Institute(
    val id: String,
    val name: String,
    val shortName: String?,
    val groupsCount: Int,
    val updatedAt: String?,
)
```

- [ ] **Step 6.2: `Lesson.kt`**

```kotlin
package ru.mpgu.rasp.data.model

data class Lesson(
    val slot: Int?,
    val timeStart: String,
    val timeEnd: String,
    val subject: String,
    val type: String?,      // lecture / practice / lab / seminar / other
    val teacher: String?,
    val room: String?,
    val subgroup: Int?,     // 1 or 2 (podgruppa), null if lesson covers full group
    val notes: String?,
)
```

- [ ] **Step 6.3: `WeekSchedule.kt`**

```kotlin
package ru.mpgu.rasp.data.model

/** Both weeks of a group's schedule. Days are Monday..Sunday keyed by DayOfWeek. */
data class WeekSchedule(
    val oddWeek: Map<java.time.DayOfWeek, List<Lesson>>,
    val evenWeek: Map<java.time.DayOfWeek, List<Lesson>>,
)
```

- [ ] **Step 6.4: `Group.kt`**

```kotlin
package ru.mpgu.rasp.data.model

data class Group(
    val name: String,
    val year: Int?,
    val form: String?,       // full_time, part_time, ...
    val degree: String?,     // bachelor, master, specialist, ...
    val schedule: WeekSchedule,
)
```

- [ ] **Step 6.5: Compile check + commit**

```bash
cd android && ./gradlew :app:compileDebugKotlin && \
  git add android/app/src/main/java/ru/mpgu/rasp/data/model && \
  git commit -m "feat(android): domain models — Institute, Group, Lesson, WeekSchedule"
```

---

## Task 7: Remote — DTOs, mappers, Ktor API

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/remote/dto/IndexDto.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/remote/dto/ScheduleManifestDto.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/remote/dto/GroupScheduleDto.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/remote/dto/LessonDto.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/remote/DtoMappers.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/remote/ScheduleApi.kt`

The endpoint contract mirrors what the PWA reads today:

- `GET {BASE}/meta/index.json` → `IndexDto`
- `GET {BASE}/institutes/{id}/schedule.json` → `ScheduleManifestDto`
- `GET {BASE}/institutes/{id}/groups/{groupFile}.json` → `GroupScheduleDto`

Default `BASE` = `https://cdn.jsdelivr.net/gh/mvbulgakova/mpgu-rasp@data`, same as PWA `vite.config.ts`.

- [ ] **Step 7.1: `LessonDto.kt`**

```kotlin
package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class LessonDto(
    val slot: Int? = null,
    val time_start: String,
    val time_end: String,
    val subject: String,
    val type: String? = null,
    val teacher: String? = null,
    val room: String? = null,
    val subgroup: Int? = null,    // wire schema: 1 | 2 | null
    val notes: String? = null,
)
```

- [ ] **Step 7.2: `IndexDto.kt`**

```kotlin
package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class IndexDto(
    val institutes: List<IndexInstituteDto> = emptyList(),
)

@Serializable
data class IndexInstituteDto(
    val id: String,
    val name: String,
    val short_name: String? = null,
    val groups_count: Int = 0,
    val updated_at: String? = null,
)
```

- [ ] **Step 7.3: `ScheduleManifestDto.kt`**

```kotlin
package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class ScheduleManifestDto(
    val institute_id: String,
    val institute_name: String,
    val short_name: String? = null,
    val academic_year: String? = null,
    val updated_at: String? = null,
    val groups: List<ManifestGroupDto> = emptyList(),
)

@Serializable
data class ManifestGroupDto(
    val name: String,
    val file: String,
    val year: Int? = null,
    val form: String? = null,
    val degree: String? = null,
)
```

- [ ] **Step 7.4: `GroupScheduleDto.kt`**

```kotlin
package ru.mpgu.rasp.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class GroupScheduleDto(
    val name: String,
    val year: Int? = null,
    val form: String? = null,
    val degree: String? = null,
    val schedule: WeekMapDto = WeekMapDto(),
)

@Serializable
data class WeekMapDto(
    val odd_week: Map<String, List<LessonDto>> = emptyMap(),
    val even_week: Map<String, List<LessonDto>> = emptyMap(),
)
```

- [ ] **Step 7.5: `DtoMappers.kt`**

```kotlin
package ru.mpgu.rasp.data.remote

import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.model.Lesson
import ru.mpgu.rasp.data.model.WeekSchedule
import ru.mpgu.rasp.data.remote.dto.GroupScheduleDto
import ru.mpgu.rasp.data.remote.dto.IndexInstituteDto
import ru.mpgu.rasp.data.remote.dto.LessonDto
import ru.mpgu.rasp.data.remote.dto.WeekMapDto
import java.time.DayOfWeek

private val DAY_MAP = mapOf(
    "monday" to DayOfWeek.MONDAY,
    "tuesday" to DayOfWeek.TUESDAY,
    "wednesday" to DayOfWeek.WEDNESDAY,
    "thursday" to DayOfWeek.THURSDAY,
    "friday" to DayOfWeek.FRIDAY,
    "saturday" to DayOfWeek.SATURDAY,
    "sunday" to DayOfWeek.SUNDAY,
)

fun IndexInstituteDto.toDomain(): Institute = Institute(
    id = id, name = name, shortName = short_name,
    groupsCount = groups_count, updatedAt = updated_at,
)

fun LessonDto.toDomain(): Lesson = Lesson(
    slot = slot, timeStart = time_start, timeEnd = time_end,
    subject = subject, type = type, teacher = teacher,
    room = room, subgroup = subgroup, notes = notes,
)

private fun WeekMapDto.toWeekMap(daysMap: Map<String, List<LessonDto>>): Map<DayOfWeek, List<Lesson>> {
    val out = mutableMapOf<DayOfWeek, List<Lesson>>()
    for ((key, list) in daysMap) {
        val day = DAY_MAP[key.lowercase()] ?: continue
        out[day] = list.map { it.toDomain() }
    }
    return out
}

fun GroupScheduleDto.toDomain(): Group = Group(
    name = name, year = year, form = form, degree = degree,
    schedule = WeekSchedule(
        oddWeek = schedule.toWeekMap(schedule.odd_week),
        evenWeek = schedule.toWeekMap(schedule.even_week),
    ),
)
```

- [ ] **Step 7.6: `ScheduleApi.kt`**

```kotlin
package ru.mpgu.rasp.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.remote.dto.GroupScheduleDto
import ru.mpgu.rasp.data.remote.dto.IndexDto
import ru.mpgu.rasp.data.remote.dto.ScheduleManifestDto
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScheduleApi @Inject constructor(
    private val http: HttpClient,
    private val baseUrl: String,
) {
    suspend fun index(): List<Institute> =
        http.get("$baseUrl/meta/index.json").body<IndexDto>().institutes.map { it.toDomain() }

    suspend fun manifest(instituteId: String): ScheduleManifestDto =
        http.get("$baseUrl/institutes/$instituteId/schedule.json").body()

    suspend fun group(instituteId: String, groupFile: String): Group =
        http.get("$baseUrl/institutes/$instituteId/groups/$groupFile.json")
            .body<GroupScheduleDto>().toDomain()
}
```

- [ ] **Step 7.7: Compile check + commit**

```bash
cd android && ./gradlew :app:compileDebugKotlin && \
  git add android/app/src/main/java/ru/mpgu/rasp/data/remote android/app/src/main/java/ru/mpgu/rasp/data/model && \
  git commit -m "feat(android): Ktor ScheduleApi + DTOs + mappers to domain"
```

---

## Task 8: Local — Room DB for offline cache

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/local/entity/InstituteEntity.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/local/entity/GroupCacheEntity.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/local/dao/InstituteDao.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/local/dao/GroupCacheDao.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/local/RaspDatabase.kt`
- Modify: `android/app/build.gradle.kts` — add Room schema location

- [ ] **Step 8.1: Room schema location**

`ksp {}` is a PROJECT-level extension exposed by the `com.google.devtools.ksp` plugin (already applied in Task 1's `plugins {}` block). It lives at the top level of `app/build.gradle.kts`, OUTSIDE `android { ... }` — nesting it inside `defaultConfig { }` would fail Gradle configuration ("No such method: ksp() for DefaultConfig").

Add this block to `app/build.gradle.kts` after the closing brace of `android { }` and before `dependencies { }`:

```kotlin
// KSP is a project-level extension (from the com.google.devtools.ksp plugin);
// it lives outside android { } / defaultConfig { }. Room reads room.schemaLocation
// to export generated schemas next to the module for version-diff review.
ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}
```

No new imports are needed — the plugin's DSL is picked up automatically.

- [ ] **Step 8.2: `InstituteEntity.kt`**

```kotlin
package ru.mpgu.rasp.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "institute")
data class InstituteEntity(
    @PrimaryKey val id: String,
    val name: String,
    val shortName: String?,
    val groupsCount: Int,
    val updatedAt: String?,
    val cachedAt: Long,
)
```

- [ ] **Step 8.3: `GroupCacheEntity.kt`**

```kotlin
package ru.mpgu.rasp.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "group_cache")
data class GroupCacheEntity(
    @PrimaryKey val cacheKey: String,   // instituteId + "/" + groupFile
    val instituteId: String,
    val groupFile: String,
    val name: String,
    val json: String,                   // raw domain JSON to keep the schema flat
    val cachedAt: Long,
)
```

- [ ] **Step 8.4: `InstituteDao.kt`**

```kotlin
package ru.mpgu.rasp.data.local.dao

import androidx.room.Dao
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow
import ru.mpgu.rasp.data.local.entity.InstituteEntity

@Dao
interface InstituteDao {
    @Query("SELECT * FROM institute ORDER BY name")
    fun observeAll(): Flow<List<InstituteEntity>>

    @Upsert(entity = InstituteEntity::class)
    suspend fun upsert(items: List<InstituteEntity>)

    @Query("DELETE FROM institute")
    suspend fun clear()
}
```

- [ ] **Step 8.5: `GroupCacheDao.kt`**

```kotlin
package ru.mpgu.rasp.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import ru.mpgu.rasp.data.local.entity.GroupCacheEntity

@Dao
interface GroupCacheDao {
    @Query("SELECT * FROM group_cache WHERE cacheKey = :key LIMIT 1")
    suspend fun get(key: String): GroupCacheEntity?

    @Upsert
    suspend fun upsert(entity: GroupCacheEntity)
}
```

- [ ] **Step 8.6: `RaspDatabase.kt`**

```kotlin
package ru.mpgu.rasp.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import ru.mpgu.rasp.data.local.dao.GroupCacheDao
import ru.mpgu.rasp.data.local.dao.InstituteDao
import ru.mpgu.rasp.data.local.entity.GroupCacheEntity
import ru.mpgu.rasp.data.local.entity.InstituteEntity

@Database(
    entities = [InstituteEntity::class, GroupCacheEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class RaspDatabase : RoomDatabase() {
    abstract fun instituteDao(): InstituteDao
    abstract fun groupCacheDao(): GroupCacheDao
}
```

- [ ] **Step 8.7: Compile check + commit**

```bash
cd android && ./gradlew :app:compileDebugKotlin && \
  git add android/app/src/main/java/ru/mpgu/rasp/data/local android/app/build.gradle.kts && \
  git commit -m "feat(android): Room DB — Institute + GroupCache entities and DAOs"
```

---

## Task 9: Prefs — DataStore for selected institute/group

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/prefs/UserPrefs.kt`

- [ ] **Step 9.1: `UserPrefs.kt`**

```kotlin
package ru.mpgu.rasp.data.prefs

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore("rasp-prefs")

@Singleton
class UserPrefs @Inject constructor(@ApplicationContext private val context: Context) {

    private object Keys {
        val INSTITUTE_ID = stringPreferencesKey("institute_id")
        val GROUP_FILE = stringPreferencesKey("group_file")
        val GROUP_NAME = stringPreferencesKey("group_name")
    }

    data class Selection(val instituteId: String?, val groupFile: String?, val groupName: String?)

    val selection: Flow<Selection> = context.dataStore.data.map { p ->
        Selection(
            instituteId = p[Keys.INSTITUTE_ID],
            groupFile = p[Keys.GROUP_FILE],
            groupName = p[Keys.GROUP_NAME],
        )
    }

    suspend fun setSelection(instituteId: String, groupFile: String, groupName: String) {
        context.dataStore.edit {
            it[Keys.INSTITUTE_ID] = instituteId
            it[Keys.GROUP_FILE] = groupFile
            it[Keys.GROUP_NAME] = groupName
        }
    }

    suspend fun clear() { context.dataStore.edit { it.clear() } }
}
```

- [ ] **Step 9.2: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/data/prefs && \
git commit -m "feat(android): UserPrefs — DataStore-backed selected institute/group"
```

---

## Task 10: Repository

**File:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/data/repo/ScheduleRepository.kt`

**Strategy:**
- `refreshInstitutes()` — fetch `/meta/index.json` → upsert into Room. Fire on app start and on pull-to-refresh.
- `observeInstitutes()` — `Flow<List<Institute>>` from Room.
- `getManifest(id)` — network, no cache (small, requests only when browsing groups).
- `getGroupSchedule(instituteId, groupFile)` — network-first; on IOException, fall back to cache. On success, upsert cache. Returns `Result<Group>`.

- [ ] **Step 10.1: Implement**

```kotlin
package ru.mpgu.rasp.data.repo

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import ru.mpgu.rasp.data.local.RaspDatabase
import ru.mpgu.rasp.data.local.entity.GroupCacheEntity
import ru.mpgu.rasp.data.local.entity.InstituteEntity
import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.remote.ScheduleApi
import ru.mpgu.rasp.data.remote.dto.GroupScheduleDto
import ru.mpgu.rasp.data.remote.toDomain
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScheduleRepository @Inject constructor(
    private val api: ScheduleApi,
    private val db: RaspDatabase,
    private val json: Json,
) {
    fun observeInstitutes(): Flow<List<Institute>> =
        db.instituteDao().observeAll().map { rows ->
            rows.map { Institute(it.id, it.name, it.shortName, it.groupsCount, it.updatedAt) }
        }

    suspend fun refreshInstitutes(): Result<Unit> = runCatching {
        val fresh = api.index()
        db.instituteDao().upsert(fresh.map {
            InstituteEntity(
                id = it.id, name = it.name, shortName = it.shortName,
                groupsCount = it.groupsCount, updatedAt = it.updatedAt,
                cachedAt = System.currentTimeMillis(),
            )
        })
    }

    suspend fun getManifest(instituteId: String) = api.manifest(instituteId)

    suspend fun getGroupSchedule(instituteId: String, groupFile: String): Result<Group> {
        val key = "$instituteId/$groupFile"
        return runCatching {
            val fresh = api.group(instituteId, groupFile)
            db.groupCacheDao().upsert(
                GroupCacheEntity(
                    cacheKey = key, instituteId = instituteId, groupFile = groupFile,
                    name = fresh.name,
                    json = json.encodeToString(GroupScheduleDto.serializer(), fresh.toDto()),
                    cachedAt = System.currentTimeMillis(),
                )
            )
            fresh
        }.recoverCatching { err ->
            if (err !is IOException) throw err
            val cached = db.groupCacheDao().get(key) ?: throw err
            json.decodeFromString(GroupScheduleDto.serializer(), cached.json).toDomain()
        }
    }

    // Round-trip helper: domain Group → DTO for cache serialization.
    private fun Group.toDto(): GroupScheduleDto {
        val weekMap = ru.mpgu.rasp.data.remote.dto.WeekMapDto(
            odd_week = schedule.oddWeek.mapKeys { it.key.name.lowercase() }
                .mapValues { entry -> entry.value.map { it.toDto() } },
            even_week = schedule.evenWeek.mapKeys { it.key.name.lowercase() }
                .mapValues { entry -> entry.value.map { it.toDto() } },
        )
        return GroupScheduleDto(name = name, year = year, form = form, degree = degree, schedule = weekMap)
    }

    private fun ru.mpgu.rasp.data.model.Lesson.toDto() = ru.mpgu.rasp.data.remote.dto.LessonDto(
        slot = slot, time_start = timeStart, time_end = timeEnd, subject = subject,
        type = type, teacher = teacher, room = room, subgroup = subgroup, notes = notes,
    )
}
```

- [ ] **Step 10.2: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/data/repo && \
git commit -m "feat(android): ScheduleRepository — network-first with Room cache fallback"
```

---

## Task 11: DI — Network, Database, Prefs modules

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/di/NetworkModule.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/di/DatabaseModule.kt`

- [ ] **Step 11.1: `NetworkModule.kt`**

```kotlin
package ru.mpgu.rasp.di

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import ru.mpgu.rasp.data.remote.ScheduleApi
import javax.inject.Singleton

private const val DEFAULT_BASE = "https://cdn.jsdelivr.net/gh/mvbulgakova/mpgu-rasp@data"

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides @Singleton
    fun provideJson(): Json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    @Provides @Singleton
    fun provideHttp(json: Json): HttpClient = HttpClient(CIO) {
        install(ContentNegotiation) { json(json) }
        install(Logging) { level = LogLevel.INFO }
    }

    @Provides @Singleton
    fun provideApi(http: HttpClient): ScheduleApi = ScheduleApi(http, DEFAULT_BASE)
}
```

**Hilt binding note:** `ScheduleApi` currently has `@Inject constructor(HttpClient, String baseUrl)` (Task 7). The unqualified `String` param would cause Hilt to error "cannot resolve binding for String" if anyone ever removes the `@Provides fun provideApi` above. Since the module DOES provide `ScheduleApi` explicitly, Hilt uses the module and never sees the constructor's `String` — so this file works as-is. If you're implementing Task 11 and want to harden it against future refactors, either:
- add `@Named("baseUrl")` on both the constructor param and a `@Provides @Named("baseUrl") fun provideBaseUrl(): String = DEFAULT_BASE`, and remove `provideApi`; OR
- remove the `@Inject` annotation from `ScheduleApi`'s constructor (keeping the constructor itself) and keep the module's `provideApi` as the only path.

Either is fine. Keeping the plan's shape as-is is also fine for MVP.

- [ ] **Step 11.2: `DatabaseModule.kt`**

```kotlin
package ru.mpgu.rasp.di

import android.content.Context
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import ru.mpgu.rasp.data.local.RaspDatabase
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides @Singleton
    fun provideDb(@ApplicationContext ctx: Context): RaspDatabase =
        Room.databaseBuilder(ctx, RaspDatabase::class.java, "rasp.db")
            .fallbackToDestructiveMigration()
            .build()
}
```

- [ ] **Step 11.3: Compile check + commit**

```bash
cd android && ./gradlew :app:assembleDebug && \
  git add android/app/src/main/java/ru/mpgu/rasp/di && \
  git commit -m "feat(android): Hilt modules — Ktor client, Room DB"
```

---

## Task 12: Navigation

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/nav/Destinations.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/nav/RaspNavGraph.kt`

- [ ] **Step 12.1: `Destinations.kt`**

```kotlin
package ru.mpgu.rasp.ui.nav

sealed class Dest(val route: String) {
    data object Onboarding : Dest("onboarding")
    data object Institutes : Dest("institutes")
    data class Groups(val instituteId: String) : Dest("groups/$instituteId") {
        companion object {
            const val ROUTE = "groups/{instituteId}"
            const val ARG = "instituteId"
        }
    }
    data class Week(val instituteId: String, val groupFile: String, val groupName: String) :
        Dest("week/$instituteId/$groupFile/${java.net.URLEncoder.encode(groupName, "UTF-8")}") {
        companion object {
            const val ROUTE = "week/{instituteId}/{groupFile}/{groupName}"
            const val ARG_INST = "instituteId"
            const val ARG_FILE = "groupFile"
            const val ARG_NAME = "groupName"
        }
    }
}
```

- [ ] **Step 12.2: `RaspNavGraph.kt`**

```kotlin
package ru.mpgu.rasp.ui.nav

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import ru.mpgu.rasp.ui.groups.GroupsScreen
import ru.mpgu.rasp.ui.institutes.InstitutesScreen
import ru.mpgu.rasp.ui.onboarding.OnboardingScreen
import ru.mpgu.rasp.ui.week.WeekScreen
import java.net.URLDecoder

@Composable
fun RaspNavGraph(startDestination: String) {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = startDestination) {
        composable(Dest.Onboarding.route) {
            OnboardingScreen(
                onPicked = { inst, file, name ->
                    nav.navigate(Dest.Week(inst, file, name).route) {
                        popUpTo(Dest.Onboarding.route) { inclusive = true }
                    }
                }
            )
        }
        composable(Dest.Institutes.route) {
            InstitutesScreen(onSelect = { id -> nav.navigate(Dest.Groups(id).route) })
        }
        composable(
            Dest.Groups.ROUTE,
            arguments = listOf(navArgument(Dest.Groups.ARG) { type = NavType.StringType }),
        ) { entry ->
            val id = entry.arguments!!.getString(Dest.Groups.ARG)!!
            GroupsScreen(
                instituteId = id,
                onSelect = { file, name -> nav.navigate(Dest.Week(id, file, name).route) },
            )
        }
        composable(
            Dest.Week.ROUTE,
            arguments = listOf(
                navArgument(Dest.Week.ARG_INST) { type = NavType.StringType },
                navArgument(Dest.Week.ARG_FILE) { type = NavType.StringType },
                navArgument(Dest.Week.ARG_NAME) { type = NavType.StringType },
            ),
        ) { entry ->
            val id = entry.arguments!!.getString(Dest.Week.ARG_INST)!!
            val file = entry.arguments!!.getString(Dest.Week.ARG_FILE)!!
            val name = URLDecoder.decode(entry.arguments!!.getString(Dest.Week.ARG_NAME)!!, "UTF-8")
            WeekScreen(instituteId = id, groupFile = file, groupName = name)
        }
    }
}
```

- [ ] **Step 12.3: Wire into `MainActivity.kt`**

Replace `MainActivity` body with:

```kotlin
package ru.mpgu.rasp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.map
import ru.mpgu.rasp.data.prefs.UserPrefs
import ru.mpgu.rasp.ui.nav.Dest
import ru.mpgu.rasp.ui.nav.RaspNavGraph
import ru.mpgu.rasp.ui.theme.RaspTheme
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var prefs: UserPrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            RaspTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val start by prefs.selection
                        .map { if (it.instituteId != null && it.groupFile != null) Dest.Institutes.route else Dest.Onboarding.route }
                        .collectAsState(initial = Dest.Onboarding.route)
                    RaspNavGraph(startDestination = start)
                }
            }
        }
    }
}
```

- [ ] **Step 12.4: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/ui/nav android/app/src/main/java/ru/mpgu/rasp/MainActivity.kt && \
git commit -m "feat(android): NavGraph with Onboarding / Institutes / Groups / Week routes"
```

---

## Task 13: InstitutesScreen

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/institutes/InstitutesViewModel.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/institutes/InstitutesScreen.kt`

- [ ] **Step 13.1: `InstitutesViewModel.kt`**

```kotlin
package ru.mpgu.rasp.ui.institutes

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.repo.ScheduleRepository
import javax.inject.Inject

@HiltViewModel
class InstitutesViewModel @Inject constructor(
    private val repo: ScheduleRepository,
) : ViewModel() {

    val institutes: StateFlow<List<Institute>> =
        repo.observeInstitutes().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    init { refresh() }

    fun refresh() { viewModelScope.launch { repo.refreshInstitutes() } }
}
```

- [ ] **Step 13.2: `InstitutesScreen.kt`**

```kotlin
package ru.mpgu.rasp.ui.institutes

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R
import ru.mpgu.rasp.data.model.Institute

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InstitutesScreen(
    onSelect: (String) -> Unit,
    vm: InstitutesViewModel = hiltViewModel(),
) {
    val items by vm.institutes.collectAsState()

    Scaffold(topBar = { TopAppBar(title = { Text(stringResource(R.string.institutes_title)) }) }) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(items, key = { it.id }) { inst -> InstituteRow(inst, onClick = { onSelect(inst.id) }) }
        }
    }
}

@Composable
private fun InstituteRow(inst: Institute, onClick: () -> Unit) {
    ElevatedCard(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(16.dp)) {
            Text(inst.name, style = MaterialTheme.typography.titleMedium)
            Text("Групп: ${inst.groupsCount}", style = MaterialTheme.typography.bodySmall)
        }
    }
}
```

- [ ] **Step 13.3: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/ui/institutes && \
git commit -m "feat(android): InstitutesScreen — cards backed by observed Room list"
```

---

## Task 14: GroupsScreen

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/groups/GroupsViewModel.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/groups/GroupsScreen.kt`

- [ ] **Step 14.1: `GroupsViewModel.kt`**

```kotlin
package ru.mpgu.rasp.ui.groups

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.remote.dto.ManifestGroupDto
import ru.mpgu.rasp.data.repo.ScheduleRepository
import ru.mpgu.rasp.util.GroupSearch
import javax.inject.Inject

@HiltViewModel
class GroupsViewModel @Inject constructor(
    private val repo: ScheduleRepository,
    savedState: SavedStateHandle,
) : ViewModel() {

    private val instituteId: String = checkNotNull(savedState["instituteId"])

    data class State(
        val groups: List<ManifestGroupDto> = emptyList(),
        val query: String = "",
        val loading: Boolean = true,
        val error: String? = null,
    ) {
        val filtered: List<ManifestGroupDto>
            get() = if (query.isBlank()) groups else groups.filter {
                GroupSearch.searchKey(it.name).contains(GroupSearch.searchKey(query))
            }
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init { load() }

    fun setQuery(q: String) { _state.value = _state.value.copy(query = q) }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repo.getManifest(instituteId) }
                .onSuccess { _state.value = _state.value.copy(groups = it.groups, loading = false) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }
}
```

- [ ] **Step 14.2: `GroupsScreen.kt`**

```kotlin
package ru.mpgu.rasp.ui.groups

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroupsScreen(
    instituteId: String,
    onSelect: (groupFile: String, groupName: String) -> Unit,
    vm: GroupsViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsState()

    Scaffold(topBar = { TopAppBar(title = { Text(stringResource(R.string.groups_title)) }) }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp)) {
            OutlinedTextField(
                value = state.query,
                onValueChange = vm::setQuery,
                label = { Text(stringResource(R.string.search_groups_hint)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            LazyColumn(
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                contentPadding = PaddingValues(bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.filtered, key = { it.file }) { g ->
                    ElevatedCard(
                        modifier = Modifier.fillMaxWidth().clickable { onSelect(g.file, g.name) },
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Text(g.name, style = MaterialTheme.typography.titleMedium)
                            g.degree?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                        }
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 14.3: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/ui/groups && \
git commit -m "feat(android): GroupsScreen — manifest fetch + homoglyph-aware search"
```

---

## Task 15: WeekScreen

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/week/WeekViewModel.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/week/LessonCard.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/week/DayCard.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/week/WeekScreen.kt`

- [ ] **Step 15.1: `WeekViewModel.kt`**

```kotlin
package ru.mpgu.rasp.ui.week

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.model.Group
import ru.mpgu.rasp.data.prefs.UserPrefs
import ru.mpgu.rasp.data.repo.ScheduleRepository
import ru.mpgu.rasp.util.WeekParity
import java.net.URLDecoder
import java.time.LocalDate
import javax.inject.Inject

@HiltViewModel
class WeekViewModel @Inject constructor(
    private val repo: ScheduleRepository,
    private val prefs: UserPrefs,
    savedState: SavedStateHandle,
) : ViewModel() {

    private val instituteId: String = checkNotNull(savedState["instituteId"])
    private val groupFile: String = checkNotNull(savedState["groupFile"])
    private val groupName: String = URLDecoder.decode(checkNotNull(savedState["groupName"]), "UTF-8")

    data class State(
        val group: Group? = null,
        val showEven: Boolean = WeekParity.forDate(LocalDate.now()) == WeekParity.EVEN,
        val loading: Boolean = true,
        val error: String? = null,
        val offline: Boolean = false,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init {
        load()
        viewModelScope.launch { prefs.setSelection(instituteId, groupFile, groupName) }
    }

    fun toggleWeek() { _state.value = _state.value.copy(showEven = !_state.value.showEven) }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            repo.getGroupSchedule(instituteId, groupFile)
                .onSuccess { _state.value = _state.value.copy(group = it, loading = false) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }
}
```

- [ ] **Step 15.2: `LessonCard.kt`**

```kotlin
package ru.mpgu.rasp.ui.week

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import ru.mpgu.rasp.data.model.Lesson

@Composable
fun LessonCard(lesson: Lesson, isNow: Boolean, modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(12.dp)
    val bg = if (isNow) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
    val border = if (isNow) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline.copy(alpha = 0.15f)
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(shape)
            .background(bg)
            .border(1.dp, border, shape)
            .padding(12.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("${lesson.timeStart}–${lesson.timeEnd}", style = MaterialTheme.typography.labelMedium)
            lesson.type?.let { Text(it, style = MaterialTheme.typography.labelSmall) }
            if (isNow) Text("сейчас", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
        }
        Text(lesson.subject, style = MaterialTheme.typography.titleSmall)
        val meta = listOfNotNull(lesson.teacher, lesson.room?.let { "ауд. $it" }, lesson.subgroup?.let { "п/г $it" })
            .joinToString(" · ")
        if (meta.isNotEmpty()) Text(meta, style = MaterialTheme.typography.bodySmall)
    }
}
```

- [ ] **Step 15.3: `DayCard.kt`**

```kotlin
package ru.mpgu.rasp.ui.week

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ru.mpgu.rasp.R
import ru.mpgu.rasp.data.model.Lesson
import ru.mpgu.rasp.util.TimeSlots
import java.time.DayOfWeek
import java.time.LocalTime
import java.time.format.TextStyle
import java.util.Locale

@Composable
fun DayCard(
    day: DayOfWeek,
    lessons: List<Lesson>,
    highlightNow: Boolean,
    now: LocalTime,
) {
    val currentIdx = if (highlightNow) TimeSlots.currentLessonIndex(
        lessons.map { TimeSlots.LessonTimeRange(LocalTime.parse(it.timeStart), LocalTime.parse(it.timeEnd)) },
        now,
    ) else null

    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            day.getDisplayName(TextStyle.FULL, Locale("ru")).replaceFirstChar { it.uppercase() },
            style = MaterialTheme.typography.titleMedium,
        )
        if (lessons.isEmpty()) {
            Text(stringResource(R.string.empty_day), style = MaterialTheme.typography.bodyMedium)
        } else {
            lessons.forEachIndexed { i, l -> LessonCard(l, isNow = i == currentIdx) }
        }
    }
}
```

- [ ] **Step 15.4: `WeekScreen.kt`**

```kotlin
package ru.mpgu.rasp.ui.week

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R
import ru.mpgu.rasp.util.WeekParity
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WeekScreen(
    instituteId: String,
    groupFile: String,
    groupName: String,
    vm: WeekViewModel = hiltViewModel(),
) {
    val state by vm.state.collectAsState()
    val today = LocalDate.now().dayOfWeek
    val now = LocalTime.now()
    val isTodayInThisWeek = (WeekParity.forDate(LocalDate.now()) == WeekParity.EVEN) == state.showEven

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(groupName)
                        Text(
                            if (state.showEven) stringResource(R.string.week_title_even) else stringResource(R.string.week_title_odd),
                            style = androidx.compose.material3.MaterialTheme.typography.labelSmall,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = vm::toggleWeek) {
                        Icon(Icons.Default.SwapHoriz, contentDescription = "Сменить неделю")
                    }
                },
            )
        },
    ) { padding ->
        val week = state.group?.schedule?.let { if (state.showEven) it.evenWeek else it.oddWeek } ?: emptyMap()
        val days = listOf(
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY, DayOfWeek.SATURDAY,
        )
        LazyColumn(
            modifier = Modifier.fillMaxWidth().padding(padding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(days, key = { it.name }) { day ->
                DayCard(
                    day = day,
                    lessons = week[day] ?: emptyList(),
                    highlightNow = isTodayInThisWeek && day == today,
                    now = now,
                )
            }
        }
    }
}
```

- [ ] **Step 15.5: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/ui/week && \
git commit -m "feat(android): WeekScreen — day list, week toggle, current-lesson highlight"
```

**Cyrillic URL note (verify in Task 18 smoke test):** `ScheduleApi.group()` interpolates the group file name into the URL string (`"$baseUrl/institutes/$instituteId/groups/$groupFile.json"`). Group codes contain Cyrillic (e.g. `ВОП40-ПФК2501`). Ktor 2.x's `HttpClient.get(String)` typically percent-encodes non-ASCII path segments through `URLBuilder.takeFrom`, but behaviour has shifted across releases and this is the first task that actually exercises a Cyrillic path segment end-to-end. If Task 18's smoke test hits a 404 or malformed request for a Cyrillic-named group, fix `ScheduleApi.group()` to use `url { pathSegments = listOf("institutes", instituteId, "groups", "$groupFile.json") }` — that path is guaranteed to encode each segment individually.

---

## Task 16: OnboardingScreen

**Files:**
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/onboarding/OnboardingViewModel.kt`
- Create: `android/app/src/main/java/ru/mpgu/rasp/ui/onboarding/OnboardingScreen.kt`

Onboarding is essentially the Institutes → Groups flow presented as a one-off wizard that saves the choice and jumps to Week.

- [ ] **Step 16.1: `OnboardingViewModel.kt`**

```kotlin
package ru.mpgu.rasp.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.mpgu.rasp.data.model.Institute
import ru.mpgu.rasp.data.prefs.UserPrefs
import ru.mpgu.rasp.data.remote.dto.ManifestGroupDto
import ru.mpgu.rasp.data.repo.ScheduleRepository
import ru.mpgu.rasp.util.GroupSearch
import javax.inject.Inject

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val repo: ScheduleRepository,
    private val prefs: UserPrefs,
) : ViewModel() {

    val institutes: StateFlow<List<Institute>> =
        repo.observeInstitutes().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _picked = MutableStateFlow<Institute?>(null)
    val picked: StateFlow<Institute?> = _picked.asStateFlow()

    private val _groups = MutableStateFlow<List<ManifestGroupDto>>(emptyList())
    val groups: StateFlow<List<ManifestGroupDto>> = _groups.asStateFlow()

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    val filteredGroups: List<ManifestGroupDto>
        get() = if (_query.value.isBlank()) _groups.value
                else _groups.value.filter { GroupSearch.searchKey(it.name).contains(GroupSearch.searchKey(_query.value)) }

    init { viewModelScope.launch { repo.refreshInstitutes() } }

    fun pickInstitute(inst: Institute) {
        _picked.value = inst
        viewModelScope.launch {
            runCatching { repo.getManifest(inst.id) }.onSuccess { _groups.value = it.groups }
        }
    }

    fun setQuery(q: String) { _query.value = q }

    fun pickGroup(g: ManifestGroupDto, then: (String, String, String) -> Unit) {
        val inst = _picked.value ?: return
        viewModelScope.launch {
            prefs.setSelection(inst.id, g.file, g.name)
            then(inst.id, g.file, g.name)
        }
    }
}
```

- [ ] **Step 16.2: `OnboardingScreen.kt`**

```kotlin
package ru.mpgu.rasp.ui.onboarding

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.mpgu.rasp.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OnboardingScreen(
    onPicked: (instituteId: String, groupFile: String, groupName: String) -> Unit,
    vm: OnboardingViewModel = hiltViewModel(),
) {
    val institutes by vm.institutes.collectAsState()
    val picked by vm.picked.collectAsState()
    val query by vm.query.collectAsState()

    Scaffold(topBar = { TopAppBar(title = { Text(stringResource(R.string.onboarding_title)) }) }) { padding ->
        if (picked == null) {
            LazyColumn(
                modifier = Modifier.fillMaxWidth().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(institutes, key = { it.id }) { inst ->
                    ElevatedCard(modifier = Modifier.fillMaxWidth().clickable { vm.pickInstitute(inst) }) {
                        Column(Modifier.padding(16.dp)) {
                            Text(inst.name, style = MaterialTheme.typography.titleMedium)
                            Text("Групп: ${inst.groupsCount}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        } else {
            Column(Modifier.padding(padding).padding(16.dp)) {
                OutlinedTextField(
                    value = query,
                    onValueChange = vm::setQuery,
                    label = { Text(stringResource(R.string.search_groups_hint)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                LazyColumn(
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(vm.filteredGroups, key = { it.file }) { g ->
                        ElevatedCard(modifier = Modifier.fillMaxWidth().clickable { vm.pickGroup(g) { a, b, c -> onPicked(a, b, c) } }) {
                            Column(Modifier.padding(16.dp)) {
                                Text(g.name, style = MaterialTheme.typography.titleMedium)
                                g.degree?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                            }
                        }
                    }
                }
            }
        }
    }
}
```

- [ ] **Step 16.3: Final assembleDebug**

```bash
cd android && ./gradlew :app:assembleDebug
```

Expected: BUILD SUCCESSFUL, APK produced.

- [ ] **Step 16.4: Commit**

```bash
git add android/app/src/main/java/ru/mpgu/rasp/ui/onboarding && \
git commit -m "feat(android): OnboardingScreen — institute+group picker saved to prefs"
```

---

## Task 17: CI — build-android.yml

**File:**
- Create: `.github/workflows/build-android.yml`

- [ ] **Step 17.1: Write workflow**

```yaml
name: Build Android

on:
  push:
    branches: [main]
    paths:
      - 'android/**'
      - '.github/workflows/build-android.yml'
  pull_request:
    paths:
      - 'android/**'
  workflow_dispatch:
  release:
    types: [published]

concurrency:
  group: build-android-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'

      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
            android/.gradle
            android/app/build
          key: gradle-${{ runner.os }}-${{ hashFiles('android/**/*.gradle*', 'android/**/gradle-wrapper.properties', 'android/gradle/libs.versions.toml') }}
          restore-keys: gradle-${{ runner.os }}-

      - name: Unit tests
        working-directory: android
        run: ./gradlew :app:testDebugUnitTest

      - name: Assemble debug APK
        working-directory: android
        run: ./gradlew :app:assembleDebug

      - name: Upload debug APK
        uses: actions/upload-artifact@v4
        with:
          name: mpgu-rasp-debug
          path: android/app/build/outputs/apk/debug/app-debug.apk
          if-no-files-found: error

      - name: Attach APK to release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: android/app/build/outputs/apk/debug/app-debug.apk#mpgu-rasp.apk
```

- [ ] **Step 17.2: Commit**

```bash
git add .github/workflows/build-android.yml && \
git commit -m "ci: build Android debug APK on push + attach on release"
```

---

## Task 18: Push and verify

- [ ] **Step 18.1: Push branch**

```bash
git push -u origin claude/schedule-app-integration-ibss01
```

- [ ] **Step 18.2: Watch CI run**

Open the Actions tab of the `mpgu-rasp` repo, wait for `Build Android` to go green.
Download the APK artifact and sideload to a device to smoke-test the four screens.

- [ ] **Step 18.3: Sanity smoke-test on device**

Manual checks:
- Onboarding lists institutes fetched from jsDelivr (network required for first run).
- Selecting an institute lists groups.
- Selecting a group opens Week — today's day highlighted, current lesson has «сейчас» chip if applicable.
- Kill and relaunch — starts directly on Week for the persisted selection.
- Turn off network, relaunch — group screen still shows last data (cached), banner or no crash.

---

## Self-review checklist

- **Spec coverage:** All Этап 3 goals in the design doc — screens 1-4, Ktor+Room+Hilt+DataStore, Material 3, Compose Nav, offline fallback, APK CI — mapped to Tasks 1-17. Deferred items (widget, Wear, FCM, calendar, extra screens) explicitly listed under Non-goals.
- **Placeholder scan:** Every code block is complete. No `// implement later`. Every command has expected output where useful.
- **Type consistency:** `Institute`, `Group`, `Lesson`, `WeekSchedule` referenced identically across tasks 6, 7, 10, 13-16. `WeekParity.ODD/EVEN` referenced from Task 3, 15. `TimeSlots.LessonTimeRange` in tasks 4, 15. `GroupSearch.searchKey/filter` in tasks 5, 14, 16. Route args in Task 12 match `SavedStateHandle` keys in tasks 14, 15.
- **Known follow-ups:**
  - Instrumented UI tests for Compose — after MVP is smoke-tested.
  - Migration to Cloudflare Worker+D1 base URL — swap in `NetworkModule.DEFAULT_BASE`.
  - Handling `/diff` for incremental updates — Этап 4.
