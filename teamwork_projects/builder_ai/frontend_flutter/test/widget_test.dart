import 'package:flutter_test/flutter_test.dart';
import 'package:builder_ai_flutter/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const BuilderApp());
    expect(find.byType(BuilderApp), findsOneWidget);
  });
}
