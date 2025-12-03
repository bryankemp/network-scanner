class AppSettings {
  final int scanParallelism;
  final int dataRetentionDays;

  AppSettings({
    required this.scanParallelism,
    required this.dataRetentionDays,
  });

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    return AppSettings(
      scanParallelism: json['scan_parallelism'] as int,
      dataRetentionDays: json['data_retention_days'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'scan_parallelism': scanParallelism,
      'data_retention_days': dataRetentionDays,
    };
  }

  AppSettings copyWith({
    int? scanParallelism,
    int? dataRetentionDays,
  }) {
    return AppSettings(
      scanParallelism: scanParallelism ?? this.scanParallelism,
      dataRetentionDays: dataRetentionDays ?? this.dataRetentionDays,
    );
  }
}
