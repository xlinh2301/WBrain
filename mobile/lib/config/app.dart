import 'package:nylo_framework/nylo_framework.dart';

/* App
|--------------------------------------------------------------------------
| Application configuration settings.
| Learn more: https://nylo.dev/docs/7.x/configuration
| -------------------------------------------------------------------------
| You can access these configuration values throughout your app using:
| `AppConfig.appName`, `AppConfig.version`, etc.
|-------------------------------------------------------------------------- */

final class AppConfig {
  // The name of the application.
  static final String appName = getEnv('APP_NAME', defaultValue: 'Nylo');

  // The version of the application.
  static final String version = getEnv('APP_VERSION', defaultValue: '1.0.0');

  // The URL of the application.
  static final String appUrl = getEnv('APP_URL', defaultValue: 'http://localhost');

  // The current environment of the application.
  static final String environment =
      getEnv('APP_ENV', defaultValue: 'developing');

  // The base URL for the application's API.
  static final String apiBaseUrl = getEnv('API_BASE_URL', defaultValue: 'https://api.myflutterapp.com');

  // The path to the assets directory.
  static final String assetPath = getEnv('ASSET_PATH', defaultValue: 'assets');

  // Whether to show the splash screen on app startup.
  static final bool showSplashScreen = getEnv('SHOW_SPLASH_SCREEN', defaultValue: true);
}