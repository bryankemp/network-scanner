import 'package:flutter/material.dart';
import 'screens/scans_screen.dart';
import 'screens/schedules_screen.dart';
import 'screens/users_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/login_screen.dart';
import 'screens/change_password_screen.dart';
import 'services/auth_service.dart';

void main() {
  runApp(const NetworkScannerApp());
}

class NetworkScannerApp extends StatelessWidget {
  const NetworkScannerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Network Scanner',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const AuthWrapper(),
      routes: {
        '/login': (context) => const LoginScreen(),
        '/change-password': (context) => const ChangePasswordScreen(isRequired: true),
      },
    );
  }
}

// Wrapper to check authentication state on app start
class AuthWrapper extends StatefulWidget {
  const AuthWrapper({Key? key}) : super(key: key);

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  bool _isLoading = true;
  bool _isAuthenticated = false;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final authService = AuthService();
    final isAuthenticated = await authService.isAuthenticated();
    
    setState(() {
      _isAuthenticated = isAuthenticated;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (!_isAuthenticated) {
      return const LoginScreen();
    }

    return const MainScreen();
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({Key? key}) : super(key: key);

  @override
  _MainScreenState createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  bool _isAdmin = false;

  @override
  void initState() {
    super.initState();
    _checkRole();
  }

  void _checkRole() {
    setState(() {
      _isAdmin = AuthService().isAdmin();
    });
  }

  List<Widget> get _screens {
    if (_isAdmin) {
      return [
        const ScansScreen(),
        const SchedulesScreen(),
        const UsersScreen(),
        const SettingsScreen(),
      ];
    } else {
      // User role: only Scans screen
      return [
        const ScansScreen(),
      ];
    }
  }

  List<NavigationDestination> get _destinations {
    if (_isAdmin) {
      return const [
        NavigationDestination(
          icon: Icon(Icons.radar),
          label: 'Scans',
        ),
        NavigationDestination(
          icon: Icon(Icons.schedule),
          label: 'Schedules',
        ),
        NavigationDestination(
          icon: Icon(Icons.people),
          label: 'Users',
        ),
        NavigationDestination(
          icon: Icon(Icons.settings),
          label: 'Settings',
        ),
      ];
    } else {
      // User role: only Scans navigation
      return const [
        NavigationDestination(
          icon: Icon(Icons.radar),
          label: 'Scans',
        ),
      ];
    }
  }

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: _destinations.length > 1
          ? NavigationBar(
              selectedIndex: _selectedIndex,
              onDestinationSelected: _onItemTapped,
              destinations: _destinations,
            )
          : null,
    );
  }
}
