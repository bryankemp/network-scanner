import 'dart:convert';
import 'package:universal_html/html.dart' as html;

class AuthService {
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _userRoleKey = 'user_role';
  static const String _usernameKey = 'username';

  // Get stored access token
  String? getAccessToken() {
    return html.window.localStorage[_accessTokenKey];
  }

  // Get stored refresh token
  String? getRefreshToken() {
    return html.window.localStorage[_refreshTokenKey];
  }

  // Get stored user role
  String? getUserRole() {
    return html.window.localStorage[_userRoleKey];
  }

  // Get stored username
  String? getUsername() {
    return html.window.localStorage[_usernameKey];
  }

  // Check if user is authenticated
  Future<bool> isAuthenticated() async {
    final token = getAccessToken();
    if (token == null) return false;
    // Check if token is expired
    return !isTokenExpired(token);
  }

  // Check if user is admin
  bool isAdmin() {
    final role = getUserRole();
    return role != null && role.toUpperCase() == 'ADMIN';
  }

  // Save auth tokens (convenience method)
  void setTokens(String accessToken, String refreshToken) {
    html.window.localStorage[_accessTokenKey] = accessToken;
    html.window.localStorage[_refreshTokenKey] = refreshToken;
  }

  // Save auth tokens and user info
  void saveAuthData({
    required String accessToken,
    required String refreshToken,
    required String role,
    required String username,
  }) {
    html.window.localStorage[_accessTokenKey] = accessToken;
    html.window.localStorage[_refreshTokenKey] = refreshToken;
    html.window.localStorage[_userRoleKey] = role;
    html.window.localStorage[_usernameKey] = username;
  }

  // Clear all auth data (logout)
  void clearTokens() {
    html.window.localStorage.remove(_accessTokenKey);
    html.window.localStorage.remove(_refreshTokenKey);
    html.window.localStorage.remove(_userRoleKey);
    html.window.localStorage.remove(_usernameKey);
  }

  // Alias for clearTokens
  void logout() {
    clearTokens();
  }

  // Decode JWT payload (simple implementation without verification)
  Map<String, dynamic>? decodeToken(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) return null;

      final payload = parts[1];
      final normalized = base64.normalize(payload);
      final decoded = utf8.decode(base64.decode(normalized));
      return json.decode(decoded) as Map<String, dynamic>;
    } catch (e) {
      return null;
    }
  }

  // Check if token is expired
  bool isTokenExpired(String token) {
    final payload = decodeToken(token);
    if (payload == null) return true;

    final exp = payload['exp'] as int?;
    if (exp == null) return true;

    final expiryDate = DateTime.fromMillisecondsSinceEpoch(exp * 1000);
    return DateTime.now().isAfter(expiryDate);
  }

  // Check if access token needs refresh (within 5 minutes of expiry)
  bool needsRefresh() {
    final token = getAccessToken();
    if (token == null) return false;

    final payload = decodeToken(token);
    if (payload == null) return true;

    final exp = payload['exp'] as int?;
    if (exp == null) return true;

    final expiryDate = DateTime.fromMillisecondsSinceEpoch(exp * 1000);
    final now = DateTime.now();
    final fiveMinutesFromNow = now.add(const Duration(minutes: 5));

    return fiveMinutesFromNow.isAfter(expiryDate);
  }
}
