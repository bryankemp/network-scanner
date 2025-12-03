class Scan {
  final int id;
  final String networkRange;
  final String status;
  final int progressPercent;
  final String? progressMessage;
  final DateTime createdAt;
  final DateTime? completedAt;
  final int? totalHosts;
  final List<Host>? hosts;
  final List<Artifact>? artifacts;

  Scan({
    required this.id,
    required this.networkRange,
    required this.status,
    required this.progressPercent,
    this.progressMessage,
    required this.createdAt,
    this.completedAt,
    this.totalHosts,
    this.hosts,
    this.artifacts,
  });

  factory Scan.fromJson(Map<String, dynamic> json) {
    return Scan(
      id: json['id'],
      networkRange: json['network_range'],
      status: json['status'],
      progressPercent: json['progress_percent'] ?? 0,
      progressMessage: json['progress_message'],
      createdAt: _parseDateTime(json['created_at']),
      completedAt: json['completed_at'] != null
          ? _parseDateTime(json['completed_at'])
          : null,
      totalHosts: json['total_hosts'],
      hosts: json['hosts'] != null
          ? (json['hosts'] as List).map((h) => Host.fromJson(h)).toList()
          : null,
      artifacts: json['artifacts'] != null
          ? (json['artifacts'] as List).map((a) => Artifact.fromJson(a)).toList()
          : null,
    );
  }

  static DateTime _parseDateTime(dynamic dateStr) {
    if (dateStr == null) return DateTime.now();
    try {
      // Try standard ISO 8601 format
      return DateTime.parse(dateStr.toString());
    } catch (e) {
      // Fallback to current time if parsing fails
      print('Failed to parse date: $dateStr');
      return DateTime.now();
    }
  }
}

class Host {
  final int id;
  final String ipAddress;
  final String? hostname;
  final String status;
  final String? osType;
  final bool? isVm;
  final String? vmType;
  final String? mac;
  final String? vendor;
  final int? openPorts;
  final List<Port>? ports;
  
  // Scan progress fields
  final String scanStatus;
  final DateTime? scanStartedAt;
  final DateTime? scanCompletedAt;
  final int scanProgressPercent;
  final String? scanErrorMessage;
  final int portsDiscovered;

  Host({
    required this.id,
    required this.ipAddress,
    this.hostname,
    required this.status,
    this.osType,
    this.isVm,
    this.vmType,
    this.mac,
    this.vendor,
    this.openPorts,
    this.ports,
    required this.scanStatus,
    this.scanStartedAt,
    this.scanCompletedAt,
    required this.scanProgressPercent,
    this.scanErrorMessage,
    required this.portsDiscovered,
  });

  factory Host.fromJson(Map<String, dynamic> json) {
    return Host(
      id: json['id'],
      ipAddress: json['ip'] ?? json['ip_address'] ?? '',
      hostname: json['hostname'],
      status: json['status'] ?? 'unknown',
      osType: json['os'] ?? json['os_type'],
      isVm: json['is_vm'],
      vmType: json['vm_type'],
      mac: json['mac'],
      vendor: json['vendor'],
      openPorts: json['open_ports'],
      ports: json['ports'] != null
          ? (json['ports'] as List).map((p) => Port.fromJson(p)).toList()
          : null,
      scanStatus: json['scan_status'] ?? 'pending',
      scanStartedAt: json['scan_started_at'] != null
          ? _parseDateTime(json['scan_started_at'])
          : null,
      scanCompletedAt: json['scan_completed_at'] != null
          ? _parseDateTime(json['scan_completed_at'])
          : null,
      scanProgressPercent: json['scan_progress_percent'] ?? 0,
      scanErrorMessage: json['scan_error_message'],
      portsDiscovered: json['ports_discovered'] ?? 0,
    );
  }
  
  static DateTime _parseDateTime(dynamic dateStr) {
    if (dateStr == null) return DateTime.now();
    try {
      return DateTime.parse(dateStr.toString());
    } catch (e) {
      return DateTime.now();
    }
  }
}

class Port {
  final int id;
  final int portNumber;
  final String protocol;
  final String? service;
  final String? product;
  final String? version;
  final String? extrainfo;

  Port({
    required this.id,
    required this.portNumber,
    required this.protocol,
    this.service,
    this.product,
    this.version,
    this.extrainfo,
  });

  factory Port.fromJson(Map<String, dynamic> json) {
    return Port(
      id: json['id'],
      portNumber: json['port'] ?? json['port_number'] ?? 0,
      protocol: json['protocol'] ?? '',
      service: json['service'],
      product: json['product'],
      version: json['version'],
      extrainfo: json['extrainfo'],
    );
  }
  
  bool get isWebService {
    return service?.toLowerCase() == 'http' ||
           service?.toLowerCase() == 'https' ||
           service?.toLowerCase() == 'http-proxy' ||
           portNumber == 80 ||
           portNumber == 443 ||
           portNumber == 8080 ||
           portNumber == 8443;
  }
  
  String getUrl(String hostIp) {
    final isHttps = service?.toLowerCase() == 'https' ||
                    portNumber == 443 ||
                    portNumber == 8443;
    final protocol = isHttps ? 'https' : 'http';
    final defaultPort = isHttps ? 443 : 80;
    final portSuffix = portNumber == defaultPort ? '' : ':$portNumber';
    return '$protocol://$hostIp$portSuffix';
  }
}

class Artifact {
  final int id;
  final String type;
  final String filePath;
  final DateTime createdAt;

  Artifact({
    required this.id,
    required this.type,
    required this.filePath,
    required this.createdAt,
  });

  factory Artifact.fromJson(Map<String, dynamic> json) {
    return Artifact(
      id: json['id'],
      type: json['type'],
      filePath: json['file_path'],
      createdAt: _parseDateTime(json['created_at']),
    );
  }

  static DateTime _parseDateTime(dynamic dateStr) {
    if (dateStr == null) return DateTime.now();
    try {
      return DateTime.parse(dateStr.toString());
    } catch (e) {
      print('Failed to parse artifact date: $dateStr');
      return DateTime.now();
    }
  }
}

class NetworkStats {
  final int totalScans;
  final int totalHosts;
  final int totalVms;
  final int totalServices;
  final int recentScans;
  final int activeSchedules;
  final int failedScans;

  NetworkStats({
    required this.totalScans,
    required this.totalHosts,
    required this.totalVms,
    required this.totalServices,
    required this.recentScans,
    required this.activeSchedules,
    required this.failedScans,
  });

  factory NetworkStats.fromJson(Map<String, dynamic> json) {
    return NetworkStats(
      totalScans: json['total_scans'],
      totalHosts: json['total_hosts'],
      totalVms: json['total_vms'],
      totalServices: json['total_services'],
      recentScans: json['recent_scans'],
      activeSchedules: json['active_schedules'],
      failedScans: json['failed_scans'],
    );
  }
}
