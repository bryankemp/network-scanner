import 'package:flutter/material.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';
import 'create_schedule_dialog.dart';
import 'package:intl/intl.dart';

class SchedulesScreen extends StatefulWidget {
  const SchedulesScreen({Key? key}) : super(key: key);

  @override
  _SchedulesScreenState createState() => _SchedulesScreenState();
}

class _SchedulesScreenState extends State<SchedulesScreen> {
  final ApiService _apiService = ApiService();
  List<Schedule> _schedules = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSchedules();
  }

  Future<void> _loadSchedules() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await _apiService.getSchedules();
      setState(() {
        _schedules = response.schedules;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _toggleSchedule(Schedule schedule) async {
    try {
      await _apiService.updateSchedule(
        schedule.id,
        enabled: !schedule.enabled,
      );
      _loadSchedules();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(schedule.enabled
                ? 'Schedule disabled'
                : 'Schedule enabled'),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update schedule: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _deleteSchedule(Schedule schedule) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Schedule'),
        content: Text('Are you sure you want to delete "${schedule.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _apiService.deleteSchedule(schedule.id);
        _loadSchedules();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Schedule deleted')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to delete schedule: $e'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  Future<void> _triggerSchedule(Schedule schedule) async {
    try {
      await _apiService.triggerSchedule(schedule.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Schedule triggered')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to trigger schedule: $e'),
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
        title: const Text('Scan Schedules'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadSchedules,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final result = await showDialog(
            context: context,
            builder: (context) => const CreateScheduleDialog(),
          );
          if (result == true) {
            _loadSchedules();
          }
        },
        child: const Icon(Icons.add),
        tooltip: 'Create Schedule',
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadSchedules,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_schedules.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.schedule, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text(
              'No schedules yet',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            const Text(
              'Create a schedule to run scans automatically',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadSchedules,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _schedules.length,
        itemBuilder: (context, index) {
          final schedule = _schedules[index];
          return _buildScheduleCard(schedule);
        },
      ),
    );
  }

  Widget _buildScheduleCard(Schedule schedule) {
    final dateFormat = DateFormat('MMM d, y HH:mm');
    
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    schedule.name,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Switch(
                  value: schedule.enabled,
                  onChanged: (_) => _toggleSchedule(schedule),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _buildInfoRow(
              Icons.schedule,
              schedule.cronDescription,
              subtitle: schedule.cronExpression,
            ),
            const SizedBox(height: 4),
            _buildInfoRow(
              Icons.network_check,
              schedule.networkRange,
            ),
            if (schedule.nextRunAt != null) ...[
              const SizedBox(height: 4),
              _buildInfoRow(
                Icons.access_time,
                'Next run: ${dateFormat.format(schedule.nextRunAt!.toLocal())}',
              ),
            ],
            if (schedule.lastRunAt != null) ...[
              const SizedBox(height: 4),
              _buildInfoRow(
                Icons.history,
                'Last run: ${dateFormat.format(schedule.lastRunAt!.toLocal())}',
              ),
            ],
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: () => _triggerSchedule(schedule),
                  icon: const Icon(Icons.play_arrow, size: 18),
                  label: const Text('Run Now'),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: () async {
                    final result = await showDialog(
                      context: context,
                      builder: (context) => CreateScheduleDialog(
                        schedule: schedule,
                      ),
                    );
                    if (result == true) {
                      _loadSchedules();
                    }
                  },
                  icon: const Icon(Icons.edit, size: 18),
                  label: const Text('Edit'),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: () => _deleteSchedule(schedule),
                  icon: const Icon(Icons.delete, size: 18),
                  label: const Text('Delete'),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String text, {String? subtitle}) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(text),
              if (subtitle != null)
                Text(
                  subtitle,
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
