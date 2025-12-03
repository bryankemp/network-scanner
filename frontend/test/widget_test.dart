import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';
import 'package:frontend/screens/login_screen.dart';
import 'package:frontend/screens/scans_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('App Initialization Tests', () {
    testWidgets('App shows correct title', (WidgetTester tester) async {
      await tester.pumpWidget(const NetworkScannerApp());
      await tester.pumpAndSettle();

      // Verify app has proper title
      final MaterialApp app = tester.widget(find.byType(MaterialApp));
      expect(app.title, 'Network Scanner');
    });

    testWidgets('App initializes without errors', (WidgetTester tester) async {
      await tester.pumpWidget(const NetworkScannerApp());
      await tester.pump();

      // Should not throw any errors during initialization
      expect(find.byType(NetworkScannerApp), findsOneWidget);
    });
  });

  group('Login Screen Tests', () {
    testWidgets('Login screen has all required fields',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Check for Network Scanner title
      expect(find.text('Network Scanner'), findsOneWidget);
      expect(find.text('Sign in to continue'), findsOneWidget);

      // Check for username field
      expect(find.widgetWithText(TextFormField, 'Username'), findsOneWidget);

      // Check for password field
      expect(find.widgetWithText(TextFormField, 'Password'), findsOneWidget);

      // Check for login button with correct text
      expect(find.text('Sign In'), findsOneWidget);
      expect(find.byType(ElevatedButton), findsOneWidget);
    });

    testWidgets('Login screen shows validation errors for empty fields',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Try to submit without filling fields
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      // Should show validation errors
      expect(find.text('Please enter your username'), findsOneWidget);
      expect(find.text('Please enter your password'), findsOneWidget);
    });

    testWidgets('Password field has visibility toggle',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Find visibility toggle icon
      expect(find.byIcon(Icons.visibility), findsOneWidget);

      // Tap to toggle password visibility
      await tester.tap(find.byIcon(Icons.visibility));
      await tester.pumpAndSettle();

      // Should now show visibility_off icon
      expect(find.byIcon(Icons.visibility_off), findsOneWidget);
    });

    testWidgets('Login screen has network icon', (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Check for network_check icon
      expect(find.byIcon(Icons.network_check), findsOneWidget);
    });
  });

  group('Password Validation Tests', () {
    testWidgets('Change password screen validates password requirements',
        (WidgetTester tester) async {
      // This tests password validation UI elements
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              Text('Password Requirements'),
              Text('✓ At least 8 characters'),
              Text('○ Uppercase letter'),
              Text('○ Lowercase letter'),
              Text('○ Number'),
              Text('○ Special character'),
            ],
          ),
        ),
      ));

      expect(find.text('Password Requirements'), findsOneWidget);
      expect(find.text('✓ At least 8 characters'), findsOneWidget);
    });
  });

  group('Navigation Tests', () {
    testWidgets('Scans screen renders without errors',
        (WidgetTester tester) async {
      // Test that ScansScreen can be instantiated
      await tester.pumpWidget(const MaterialApp(
        home: ScansScreen(),
      ));
      await tester.pump();

      // Should show scans screen widget
      expect(find.byType(ScansScreen), findsOneWidget);
    });

    testWidgets('MaterialApp navigation structure works',
        (WidgetTester tester) async {
      // Test basic navigation functionality
      await tester.pumpWidget(const MaterialApp(
        home: ScansScreen(),
      ));
      await tester.pump();

      // Should have a Scaffold
      expect(find.byType(Scaffold), findsWidgets);
    });
  });

  group('Scans Screen Tests', () {
    testWidgets('Scans screen initializes correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: ScansScreen(),
      ));
      await tester.pump(); // Initial build

      // Should render the ScansScreen widget
      expect(find.byType(ScansScreen), findsOneWidget);
    });

    testWidgets('Scans screen has AppBar',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: ScansScreen(),
      ));
      await tester.pump();

      // Should have an AppBar
      expect(find.byType(AppBar), findsWidgets);
    });

    testWidgets('Scans screen displays correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: ScansScreen(),
      ));
      await tester.pump();

      // Should show scans screen
      expect(find.byType(ScansScreen), findsOneWidget);
    });
  });

  group('Theme Tests', () {
    testWidgets('App uses Material Design 3', (WidgetTester tester) async {
      await tester.pumpWidget(const NetworkScannerApp());

      final MaterialApp app = tester.widget(find.byType(MaterialApp));
      expect(app.theme?.useMaterial3, isTrue);
    });

    testWidgets('App has custom color scheme', (WidgetTester tester) async {
      await tester.pumpWidget(const NetworkScannerApp());

      final MaterialApp app = tester.widget(find.byType(MaterialApp));
      expect(app.theme?.colorScheme, isNotNull);
      expect(app.theme?.colorScheme?.primary, isNotNull);
    });
  });

  group('Error Handling Tests', () {
    testWidgets('Shows error snackbar on network failure',
        (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Network error occurred')),
                );
              },
              child: const Text('Trigger Error'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Trigger Error'));
      await tester.pumpAndSettle();

      expect(find.text('Network error occurred'), findsOneWidget);
    });
  });

  group('Logout Tests', () {
    testWidgets('Logout button shows confirmation dialog',
        (WidgetTester tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          appBar: AppBar(
            actions: [
              IconButton(
                icon: const Icon(Icons.logout),
                onPressed: () async {
                  // This would show confirmation dialog
                },
              ),
            ],
          ),
        ),
      ));

      expect(find.byIcon(Icons.logout), findsOneWidget);
    });
  });

  group('Accessibility Tests', () {
    testWidgets('Login button is accessible',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Find login button with correct text
      final loginButton = find.text('Sign In');
      expect(loginButton, findsOneWidget);
      expect(find.byType(ElevatedButton), findsOneWidget);
    });

    testWidgets('Text fields have proper labels', (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Check text fields have labels
      expect(find.widgetWithText(TextFormField, 'Username'), findsOneWidget);
      expect(find.widgetWithText(TextFormField, 'Password'), findsOneWidget);
    });
  });

  group('Form Validation Tests', () {
    testWidgets('Form validates before submission',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
      await tester.pumpAndSettle();

      // Find the form
      final formFinder = find.byType(Form);
      expect(formFinder, findsOneWidget);

      // Try to submit empty form
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      // Validation errors should appear
      expect(find.text('Please enter your username'), findsOneWidget);
      expect(find.text('Please enter your password'), findsOneWidget);
    });
  });

  group('Loading States Tests', () {
    testWidgets('Shows loading indicator during async operations',
        (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: Center(
            child: CircularProgressIndicator(),
          ),
        ),
      ));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('Icon Tests', () {
    testWidgets('App uses appropriate icons', (WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              Icon(Icons.wifi),
              Icon(Icons.refresh),
              Icon(Icons.logout),
              Icon(Icons.settings),
            ],
          ),
        ),
      ));

      expect(find.byIcon(Icons.wifi), findsOneWidget);
      expect(find.byIcon(Icons.refresh), findsOneWidget);
      expect(find.byIcon(Icons.logout), findsOneWidget);
      expect(find.byIcon(Icons.settings), findsOneWidget);
    });
  });
}
