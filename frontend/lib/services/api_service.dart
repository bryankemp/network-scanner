import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/scan.dart';
import '../models/schedule.dart';
import '../models/settings.dart';
import 'package:universal_html/html.dart' as html;
import 'auth_service.dart';

class ApiService {
  // Dynamic base URL that uses the current host
  static String get baseUrl {
    final currentHost = html.window.location.host;
    final protocol = html.window.location.protocol;
    return '$protocol//$currentHost/api';
  }

  // Get headers with optional auth token
  Map<String, String> _getHeaders({bool includeAuth = true}) {
    final headers = {'Content-Type': 'application/json'};
    
    if (includeAuth) {
      final token = AuthService().getAccessToken();
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    
    return headers;
  }

  // Handle 401 responses by redirecting to login
  void _handleUnauthorized() {
    AuthService().clearTokens();
    // Navigate to login will be handled by the app checking isAuthenticated
  }

  // Authentication endpoints
  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'username': username,
        'password': password,
      }),
    );
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else if (response.statusCode == 401) {
      throw Exception('Incorrect username or password');
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  Future<void> changePassword(String currentPassword, String newPassword) async {
    final response = await http.put(
      Uri.parse('$baseUrl/auth/change-password'),
      headers: _getHeaders(),
      body: json.encode({
        'current_password': currentPassword,
        'new_password': newPassword,
      }),
    );
    
    if (response.statusCode == 200) {
      return;
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else if (response.statusCode == 400) {
      throw Exception('Current password is incorrect');
    } else {
      throw Exception('Failed to change password: ${response.body}');
    }
  }

  Future<List<Scan>> getScans() async {
    final response = await http.get(Uri.parse('$baseUrl/scans'));
    
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => Scan.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load scans');
    }
  }

  Future<Scan> getScan(int id) async {
    final response = await http.get(Uri.parse('$baseUrl/scans/$id'));
    
    if (response.statusCode == 200) {
      return Scan.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load scan');
    }
  }

  Future<Scan> createScan({List<String>? networks}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/scans'),
      headers: _getHeaders(),
      body: json.encode({
        'networks': networks,
      }),
    );
    
    if (response.statusCode == 201) {
      return Scan.fromJson(json.decode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to create scan: ${response.body}');
    }
  }

  Future<void> deleteScan(int id) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/scans/$id'),
      headers: _getHeaders(),
    );
    
    if (response.statusCode == 204) {
      return;
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to delete scan');
    }
  }

  Future<NetworkStats> getStats() async {
    final response = await http.get(Uri.parse('$baseUrl/stats'));
    
    if (response.statusCode == 200) {
      return NetworkStats.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load stats');
    }
  }

  String getArtifactUrl(int scanId, String type) {
    return '$baseUrl/artifacts/$scanId/$type';
  }

  // Schedule endpoints
  Future<ScheduleListResponse> getSchedules({int skip = 0, int limit = 50}) async {
    final response = await http.get(
      Uri.parse('$baseUrl/schedules?skip=$skip&limit=$limit'),
    );
    
    if (response.statusCode == 200) {
      return ScheduleListResponse.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load schedules');
    }
  }

  Future<Schedule> getSchedule(int id) async {
    final response = await http.get(Uri.parse('$baseUrl/schedules/$id'));
    
    if (response.statusCode == 200) {
      return Schedule.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load schedule');
    }
  }

  Future<Schedule> createSchedule({
    required String name,
    required String cronExpression,
    required String networkRange,
    bool enabled = true,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/schedules'),
      headers: _getHeaders(),
      body: json.encode({
        'name': name,
        'cron_expression': cronExpression,
        'network_range': networkRange,
        'enabled': enabled,
      }),
    );
    
    if (response.statusCode == 201) {
      return Schedule.fromJson(json.decode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to create schedule: ${response.body}');
    }
  }

  Future<Schedule> updateSchedule(
    int id, {
    String? name,
    String? cronExpression,
    String? networkRange,
    bool? enabled,
  }) async {
    final Map<String, dynamic> body = {};
    if (name != null) body['name'] = name;
    if (cronExpression != null) body['cron_expression'] = cronExpression;
    if (networkRange != null) body['network_range'] = networkRange;
    if (enabled != null) body['enabled'] = enabled;

    final response = await http.put(
      Uri.parse('$baseUrl/schedules/$id'),
      headers: _getHeaders(),
      body: json.encode(body),
    );
    
    if (response.statusCode == 200) {
      return Schedule.fromJson(json.decode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to update schedule: ${response.body}');
    }
  }

  Future<void> deleteSchedule(int id) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/schedules/$id'),
      headers: _getHeaders(),
    );
    
    if (response.statusCode == 204) {
      return;
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to delete schedule');
    }
  }

  Future<void> triggerSchedule(int id) async {
    final response = await http.post(
      Uri.parse('$baseUrl/schedules/$id/trigger'),
      headers: _getHeaders(),
    );
    
    if (response.statusCode == 200) {
      return;
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to trigger schedule');
    }
  }

  // Unique data endpoints
  Future<List<Host>> getUniqueHosts() async {
    final response = await http.get(Uri.parse('$baseUrl/hosts/unique'));
    
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => Host.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load unique hosts');
    }
  }

  Future<List<Host>> getUniqueVMs() async {
    final response = await http.get(Uri.parse('$baseUrl/vms/unique'));
    
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => Host.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load unique VMs');
    }
  }

  Future<Map<String, dynamic>> getUniqueServices() async {
    final response = await http.get(Uri.parse('$baseUrl/services/unique'));
    
    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load unique services');
    }
  }

  // Settings endpoints
  Future<AppSettings> getSettings() async {
    final response = await http.get(Uri.parse('$baseUrl/settings'));
    
    if (response.statusCode == 200) {
      return AppSettings.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load settings');
    }
  }

  Future<AppSettings> updateSettings(AppSettings settings) async {
    final response = await http.put(
      Uri.parse('$baseUrl/settings'),
      headers: _getHeaders(),
      body: json.encode(settings.toJson()),
    );
    
    if (response.statusCode == 200) {
      return AppSettings.fromJson(json.decode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to update settings: ${response.body}');
    }
  }

  // User management endpoints (admin only)
  Future<List<Map<String, dynamic>>> getUsers() async {
    final response = await http.get(
      Uri.parse('$baseUrl/users'),
      headers: _getHeaders(),
    );
    
    if (response.statusCode == 200) {
      final Map<String, dynamic> responseData = json.decode(response.body);
      final List<dynamic> users = responseData['users'];
      return users.cast<Map<String, dynamic>>();
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to load users: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> createUser({
    required String username,
    required String password,
    String? email,
    String? fullName,
    String role = 'USER',
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users'),
      headers: _getHeaders(),
      body: json.encode({
        'username': username,
        'password': password,
        if (email != null) 'email': email,
        if (fullName != null) 'full_name': fullName,
        'role': role,
      }),
    );
    
    if (response.statusCode == 201) {
      return json.decode(response.body);
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to create user: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> updateUser({
    required int userId,
    String? email,
    String? fullName,
    String? role,
    bool? isActive,
  }) async {
    final Map<String, dynamic> body = {};
    // Only include fields that are not null and not empty strings
    if (email != null && email.isNotEmpty) body['email'] = email;
    if (fullName != null && fullName.isNotEmpty) body['full_name'] = fullName;
    if (role != null && role.isNotEmpty) body['role'] = role;
    if (isActive != null) body['is_active'] = isActive;

    final response = await http.put(
      Uri.parse('$baseUrl/users/$userId'),
      headers: _getHeaders(),
      body: json.encode(body),
    );
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to update user: ${response.body}');
    }
  }

  Future<void> deleteUser(int userId) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/users/$userId'),
      headers: _getHeaders(),
    );
    
    if (response.statusCode == 204) {
      return;
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to delete user: ${response.body}');
    }
  }

  Future<void> resetUserPassword({
    required int userId,
    required String newPassword,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users/$userId/reset-password'),
      headers: _getHeaders(),
      body: json.encode({
        'new_password': newPassword,
      }),
    );
    
    if (response.statusCode == 200) {
      return;
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Not authenticated');
    } else {
      throw Exception('Failed to reset password: ${response.body}');
    }
  }
}
