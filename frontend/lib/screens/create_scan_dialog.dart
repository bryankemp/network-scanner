import 'package:flutter/material.dart';

class CreateScanDialog extends StatefulWidget {
  const CreateScanDialog({super.key});

  @override
  State<CreateScanDialog> createState() => _CreateScanDialogState();
}

class _CreateScanDialogState extends State<CreateScanDialog> {
  final _formKey = GlobalKey<FormState>();
  final _networkController = TextEditingController();
  final List<String> _networks = [];
  bool _autoDetect = false;  // Default to manual since auto-detect may not work in container

  void _addNetwork() {
    if (_networkController.text.isNotEmpty) {
      setState(() {
        _networks.add(_networkController.text.trim());
        _networkController.clear();
      });
    }
  }

  void _removeNetwork(int index) {
    setState(() {
      _networks.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Create New Scan'),
      content: SizedBox(
        width: 500,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Enter network(s) to scan in CIDR format:',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 8),
              const Text(
                'Examples: 192.168.1.0/24, 10.0.0.0/16',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _networkController,
                      decoration: const InputDecoration(
                        labelText: 'Network CIDR',
                        hintText: '192.168.1.0/24',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.router),
                      ),
                      onFieldSubmitted: (_) => _addNetwork(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    icon: const Icon(Icons.add),
                    tooltip: 'Add network',
                    onPressed: _addNetwork,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (_networks.isNotEmpty) ...[
                const Text(
                  'Networks to scan:',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _networks.asMap().entries.map((entry) {
                    return Chip(
                      label: Text(entry.value),
                      deleteIcon: const Icon(Icons.close, size: 18),
                      onDeleted: () => _removeNetwork(entry.key),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 8),
              ],
              const Divider(),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Auto-detect network (experimental)'),
                subtitle: const Text('May not work in containerized environments'),
                value: _autoDetect,
                dense: true,
                onChanged: (value) {
                  setState(() {
                    _autoDetect = value;
                  });
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton.icon(
          onPressed: () {
            if (_autoDetect) {
              Navigator.pop(context, <String>[]);
            } else if (_networks.isNotEmpty) {
              Navigator.pop(context, _networks);
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Please add at least one network to scan'),
                  backgroundColor: Colors.orange,
                ),
              );
            }
          },
          icon: const Icon(Icons.radar),
          label: const Text('Start Scan'),
        ),
      ],
    );
  }

  @override
  void dispose() {
    _networkController.dispose();
    super.dispose();
  }
}
