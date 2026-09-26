plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.assistentevoz.callscreening"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.assistentevoz.callscreening"
        // CallScreeningService requer API 24+
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0-skeleton"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}
