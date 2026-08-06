import 'package:flutter/material.dart';

/// Standard full-screen/section loading indicator (Band 18: reusable
/// widgets) — the one spinner every screen's loading state should use.
class LoadingView extends StatelessWidget {
  const LoadingView({super.key});

  @override
  Widget build(BuildContext context) => const Center(child: CircularProgressIndicator());
}
