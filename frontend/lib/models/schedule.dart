class Schedule {
  final int id;
  final String name;
  final String cronExpression;
  final String networkRange;
  final bool enabled;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? lastRunAt;
  final DateTime? nextRunAt;
  final int createdById;

  Schedule({
    required this.id,
    required this.name,
    required this.cronExpression,
    required this.networkRange,
    required this.enabled,
    required this.createdAt,
    required this.updatedAt,
    this.lastRunAt,
    this.nextRunAt,
    required this.createdById,
  });

  factory Schedule.fromJson(Map<String, dynamic> json) {
    return Schedule(
      id: json['id'],
      name: json['name'],
      cronExpression: json['cron_expression'],
      networkRange: json['network_range'],
      enabled: json['enabled'] ?? false,
      createdAt: _parseDateTime(json['created_at']),
      updatedAt: _parseDateTime(json['updated_at']),
      lastRunAt: json['last_run_at'] != null
          ? _parseDateTime(json['last_run_at'])
          : null,
      nextRunAt: json['next_run_at'] != null
          ? _parseDateTime(json['next_run_at'])
          : null,
      createdById: json['created_by_id'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'cron_expression': cronExpression,
      'network_range': networkRange,
      'enabled': enabled,
    };
  }

  static DateTime _parseDateTime(dynamic dateStr) {
    if (dateStr == null) return DateTime.now();
    try {
      return DateTime.parse(dateStr.toString());
    } catch (e) {
      print('Failed to parse date: $dateStr');
      return DateTime.now();
    }
  }

  String get cronDescription {
    final parts = cronExpression.split(' ');
    if (parts.length != 5) return cronExpression;
    
    final minute = parts[0];
    final hour = parts[1];
    final day = parts[2];
    final month = parts[3];
    final dayOfWeek = parts[4];

    // Simple descriptions for common patterns
    if (cronExpression == '* * * * *') return 'Every minute';
    if (cronExpression == '0 * * * *') return 'Every hour';
    if (cronExpression == '0 0 * * *') return 'Daily at midnight';
    if (cronExpression == '0 2 * * *') return 'Daily at 2:00 AM';
    if (cronExpression == '0 */6 * * *') return 'Every 6 hours';
    if (cronExpression == '0 0 * * 0') return 'Weekly on Sunday';
    if (cronExpression == '0 0 1 * *') return 'Monthly on the 1st';
    if (minute.startsWith('*/') && hour == '*' && day == '*' && month == '*' && dayOfWeek == '*') {
      return 'Every ${minute.substring(2)} minutes';
    }
    
    return cronExpression;
  }
}

class ScheduleListResponse {
  final List<Schedule> schedules;
  final int total;

  ScheduleListResponse({
    required this.schedules,
    required this.total,
  });

  factory ScheduleListResponse.fromJson(Map<String, dynamic> json) {
    return ScheduleListResponse(
      schedules: (json['schedules'] as List)
          .map((s) => Schedule.fromJson(s))
          .toList(),
      total: json['total'],
    );
  }
}
