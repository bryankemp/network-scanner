import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'package:universal_html/html.dart' as html;

class ServicesListScreen extends StatefulWidget {
  const ServicesListScreen({Key? key}) : super(key: key);

  @override
  _ServicesListScreenState createState() => _ServicesListScreenState();
}

class _ServicesListScreenState extends State<ServicesListScreen> {
  final ApiService _apiService = ApiService();
  Map<String, dynamic> _services = {};
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadServices();
  }

  Future<void> _loadServices() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final services = await _apiService.getUniqueServices();
      setState(() {
        _services = services;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Services'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadServices,
          ),
        ],
      ),
      body: _buildBody(),
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
              onPressed: _loadServices,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_services.isEmpty) {
      return const Center(
        child: Text('No services found', style: TextStyle(fontSize: 18, color: Colors.grey)),
      );
    }

    final serviceNames = _services.keys.toList()..sort();

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: serviceNames.length,
      itemBuilder: (context, index) {
        final serviceName = serviceNames[index];
        final products = _services[serviceName] as Map<String, dynamic>;
        return _buildServiceCard(serviceName, products);
      },
    );
  }

  Widget _buildServiceCard(String serviceName, Map<String, dynamic> products) {
    final productKeys = products.keys.toList()..sort();
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ExpansionTile(
        leading: const Icon(Icons.memory),
        title: Text(
          serviceName.toUpperCase(),
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text('${productKeys.length} version(s)'),
        children: productKeys.map((productKey) {
          final instances = products[productKey] as List;
          final hostsList = <String>{};
          for (var instance in instances) {
            final hosts = instance['hosts'] as List;
            hostsList.addAll(hosts.cast<String>());
          }
          
          // Determine if this is a web service
          final isWebService = serviceName.toLowerCase() == 'http' || 
                               serviceName.toLowerCase() == 'https' ||
                               serviceName.toLowerCase() == 'http-proxy' ||
                               serviceName.toLowerCase() == 'ssl/http';
          
          return ExpansionTile(
            title: Text(productKey, style: const TextStyle(fontSize: 14)),
            subtitle: Text('${hostsList.length} host(s)'),
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ...hostsList.map((host) {
                      // Extract port from host string if present (format: ip or ip:port)
                      final hostParts = host.split(':');
                      final ip = hostParts[0];
                      final port = hostParts.length > 1 ? hostParts[1] : null;
                      
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: isWebService && port != null
                            ? InkWell(
                                onTap: () {
                                  final protocol = serviceName.toLowerCase().contains('https') || port == '443' 
                                      ? 'https' 
                                      : 'http';
                                  final url = port == '80' || port == '443'
                                      ? '$protocol://$ip'
                                      : '$protocol://$ip:$port';
                                  html.window.open(url, '_blank');
                                },
                                child: Row(
                                  children: [
                                    const Icon(Icons.open_in_new, size: 14, color: Colors.blue),
                                    const SizedBox(width: 8),
                                    Text(
                                      host,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: Colors.blue,
                                        decoration: TextDecoration.underline,
                                      ),
                                    ),
                                  ],
                                ),
                              )
                            : Row(
                                children: [
                                  const Icon(Icons.computer, size: 14, color: Colors.grey),
                                  const SizedBox(width: 8),
                                  Text(host, style: const TextStyle(fontSize: 12)),
                                ],
                              ),
                      );
                    }),
                  ],
                ),
              ),
            ],
          );
        }).toList(),
      ),
    );
  }
}
