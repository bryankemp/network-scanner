import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/settings.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import 'change_password_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  _SettingsScreenState createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final ApiService _apiService = ApiService();
  final _formKey = GlobalKey<FormState>();
  
  AppSettings? _settings;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  
  late TextEditingController _parallelismController;
  late TextEditingController _retentionController;

  @override
  void initState() {
    super.initState();
    _parallelismController = TextEditingController();
    _retentionController = TextEditingController();
    _loadSettings();
  }

  @override
  void dispose() {
    _parallelismController.dispose();
    _retentionController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final settings = await _apiService.getSettings();
      setState(() {
        _settings = settings;
        _parallelismController.text = settings.scanParallelism.toString();
        _retentionController.text = settings.dataRetentionDays.toString();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final updatedSettings = AppSettings(
        scanParallelism: int.parse(_parallelismController.text),
        dataRetentionDays: int.parse(_retentionController.text),
      );

      final result = await _apiService.updateSettings(updatedSettings);
      
      setState(() {
        _settings = result;
        _saving = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _saving = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save settings: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadSettings,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: Colors.red),
                      const SizedBox(height: 16),
                      Text('Error: $_error'),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadSettings,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.tune, size: 28),
                                    const SizedBox(width: 12),
                                    Text(
                                      'Scan Configuration',
                                      style: Theme.of(context).textTheme.titleLarge,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                TextFormField(
                                  controller: _parallelismController,
                                  decoration: const InputDecoration(
                                    labelText: 'Concurrent Host Scans',
                                    hintText: 'Number of parallel scans (1-32)',
                                    helperText: 'Higher values scan faster but use more resources',
                                    prefixIcon: Icon(Icons.speed),
                                    border: OutlineInputBorder(),
                                  ),
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [
                                    FilteringTextInputFormatter.digitsOnly,
                                  ],
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter a value';
                                    }
                                    final num = int.tryParse(value);
                                    if (num == null || num < 1 || num > 32) {
                                      return 'Must be between 1 and 32';
                                    }
                                    return null;
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.account_circle, size: 28),
                                    const SizedBox(width: 12),
                                    Text(
                                      'Account',
                                      style: Theme.of(context).textTheme.titleLarge,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                ListTile(
                                  leading: const Icon(Icons.lock_reset),
                                  title: const Text('Change Password'),
                                  subtitle: const Text('Update your account password'),
                                  trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                                  onTap: () {
                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) => const ChangePasswordScreen(),
                                      ),
                                    );
                                  },
                                ),
                                const Divider(),
                                ListTile(
                                  leading: const Icon(Icons.logout, color: Colors.red),
                                  title: const Text(
                                    'Logout',
                                    style: TextStyle(color: Colors.red),
                                  ),
                                  subtitle: const Text('Sign out of your account'),
                                  trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                                  onTap: () async {
                                    final confirm = await showDialog<bool>(
                                      context: context,
                                      builder: (context) => AlertDialog(
                                        title: const Text('Logout'),
                                        content: const Text('Are you sure you want to logout?'),
                                        actions: [
                                          TextButton(
                                            onPressed: () => Navigator.pop(context, false),
                                            child: const Text('Cancel'),
                                          ),
                                          TextButton(
                                            onPressed: () => Navigator.pop(context, true),
                                            child: const Text(
                                              'Logout',
                                              style: TextStyle(color: Colors.red),
                                            ),
                                          ),
                                        ],
                                      ),
                                    );

                                    if (confirm == true && mounted) {
                                      AuthService().clearTokens();
                                      if (mounted) {
                                        Navigator.pushReplacementNamed(context, '/login');
                                      }
                                    }
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.delete_sweep, size: 28),
                                    const SizedBox(width: 12),
                                    Text(
                                      'Data Retention',
                                      style: Theme.of(context).textTheme.titleLarge,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                TextFormField(
                                  controller: _retentionController,
                                  decoration: const InputDecoration(
                                    labelText: 'Data Retention Period (Days)',
                                    hintText: 'Keep scan data for X days (1-365)',
                                    helperText: 'Old scans are deleted daily at 2 AM UTC',
                                    prefixIcon: Icon(Icons.calendar_today),
                                    border: OutlineInputBorder(),
                                  ),
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [
                                    FilteringTextInputFormatter.digitsOnly,
                                  ],
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Please enter a value';
                                    }
                                    final num = int.tryParse(value);
                                    if (num == null || num < 1 || num > 365) {
                                      return 'Must be between 1 and 365 days';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 12),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.orange.shade50,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: Colors.orange.shade200),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(Icons.info_outline, color: Colors.orange.shade700, size: 20),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          'Scan data older than this period will be permanently deleted to free disk space',
                                          style: TextStyle(
                                            fontSize: 13,
                                            color: Colors.orange.shade900,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          height: 48,
                          child: ElevatedButton.icon(
                            onPressed: _saving ? null : _saveSettings,
                            icon: _saving
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.save),
                            label: Text(_saving ? 'Saving...' : 'Save Settings'),
                            style: ElevatedButton.styleFrom(
                              textStyle: const TextStyle(fontSize: 16),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }
}
