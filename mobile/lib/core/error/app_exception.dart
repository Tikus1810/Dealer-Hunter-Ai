/// A typed, user-presentable error. Mirrors the backend's unified error
/// model (`ErrorResponse{code, message, details, correlation_id}` — Band
/// 10) so a server-raised `DomainError` and a client-side network failure
/// look the same to every screen.
class AppException implements Exception {
  const AppException({
    required this.code,
    required this.message,
    this.details,
    this.correlationId,
    this.statusCode,
  });

  final String code;
  final String message;
  final Map<String, dynamic>? details;
  final String? correlationId;
  final int? statusCode;

  factory AppException.network() => const AppException(
        code: 'network_error',
        message: 'Keine Verbindung zum Server. Bitte Internetverbindung prüfen.',
      );

  factory AppException.unknown([Object? cause]) => AppException(
        code: 'unknown_error',
        message: 'Ein unerwarteter Fehler ist aufgetreten.',
        details: cause == null ? null : <String, dynamic>{'cause': cause.toString()},
      );

  @override
  String toString() => 'AppException($code): $message';
}
