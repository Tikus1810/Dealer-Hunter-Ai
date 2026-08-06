/// App-wide configuration, resolved from compile-time environment
/// variables (`--dart-define`) — mirrors the backend's `Settings` pattern
/// (`backend/app/core/config.py`): one typed object, read once, no
/// framework dependency.
class AppConfig {
  const AppConfig({required this.apiBaseUrl});

  final String apiBaseUrl;

  /// Defaults to a local backend for development
  /// (`uvicorn app.main:app --reload`, see `backend/README.md`). Override
  /// with `flutter run --dart-define=API_BASE_URL=https://api.example.com/api/v1`.
  factory AppConfig.fromEnvironment() {
    const apiBaseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://localhost:8000/api/v1',
    );
    return const AppConfig(apiBaseUrl: apiBaseUrl);
  }
}
