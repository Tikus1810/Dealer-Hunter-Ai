import 'package:deal_hunter_ai/core/error/error_mapper.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const mapper = ErrorMapper();

  test('maps a backend ErrorResponse body to a matching AppException', () {
    final requestOptions = RequestOptions(path: '/offers/123');
    final response = Response<Map<String, dynamic>>(
      requestOptions: requestOptions,
      statusCode: 404,
      data: {
        'code': 'not_found',
        'message': 'offer not found',
        'details': {'offer_id': '123'},
        'correlation_id': 'abc-123',
      },
    );
    final dioError = DioException(requestOptions: requestOptions, response: response);

    final result = mapper.mapDioException(dioError);

    expect(result.code, 'not_found');
    expect(result.message, 'offer not found');
    expect(result.correlationId, 'abc-123');
    expect(result.statusCode, 404);
    expect(result.details, {'offer_id': '123'});
  });

  test('maps a connection timeout to a network AppException', () {
    final requestOptions = RequestOptions(path: '/offers');
    final dioError = DioException(
      requestOptions: requestOptions,
      type: DioExceptionType.connectionTimeout,
    );

    final result = mapper.mapDioException(dioError);

    expect(result.code, 'network_error');
  });

  test('maps a connection error to a network AppException', () {
    final requestOptions = RequestOptions(path: '/offers');
    final dioError = DioException(
      requestOptions: requestOptions,
      type: DioExceptionType.connectionError,
    );

    final result = mapper.mapDioException(dioError);

    expect(result.code, 'network_error');
  });

  test('falls back to unknown_error for an unrecognized error body', () {
    final requestOptions = RequestOptions(path: '/offers');
    final dioError = DioException(requestOptions: requestOptions);

    final result = mapper.mapDioException(dioError);

    expect(result.code, 'unknown_error');
  });

  test('falls back to unknown_error when the response body has no code/message', () {
    final requestOptions = RequestOptions(path: '/offers');
    final response = Response<Map<String, dynamic>>(
      requestOptions: requestOptions,
      statusCode: 500,
      data: {'detail': 'Internal Server Error'},
    );
    final dioError = DioException(requestOptions: requestOptions, response: response);

    final result = mapper.mapDioException(dioError);

    expect(result.code, 'unknown_error');
  });
}
