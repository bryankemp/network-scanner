import 'package:flutter/material.dart';
import '../models/schedule.dart';
import '../services/api_service.dart';

class CreateScheduleDialog extends StatefulWidget {
  final Schedule? schedule;

  const CreateScheduleDialog({Key? key, this.schedule}) : super(key: key);

  @override
  _CreateScheduleDialogState createState() => _CreateScheduleDialogState();
}

class _CreateScheduleDialogState extends State<CreateScheduleDialog> {
  final _formKey = GlobalKey<FormState>();
  final ApiService _apiService = ApiService();
  
  late TextEditingController _nameController;
  late TextEditingController _cronController;
  late TextEditingController _networkController;
  bool _enabled = true;
  bool _loading = false;
  String? _selectedPreset;

  final Map<String, String> _cronPresets = {
    'Every 15 minutes': '*/15 * * * *',
    'Every hour': '0 * * * *',
    'Every 6 hours': '0 */6 * * *',
    'Daily at 2 AM': '0 2 * * *',
    'Daily at midnight': '0 0 * * *',
    'Weekly on Sunday': '0 0 * * 0',
    'Monthly on 1st': '0 0 1 * *',
    'Business hours (Mon-Fri, hourly)': '0 9-17 * * 1-5',
    'Custom': '',
  };

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.schedule?.name ?? '');
    _cronController = TextEditingController(
      text: widget.schedule?.cronExpression ?? '0 2 * * *',
    );
    _networkController = TextEditingController(
      text: widget.schedule?.networkRange ?? '',
    );
    _enabled = widget.schedule?.enabled ?? true;
    
    // Set preset based on existing cron expression
    if (widget.schedule != null) {
      for (var entry in _cronPresets.entries) {
        if (entry.value == widget.schedule!.cronExpression) {
          _selectedPreset = entry.key;
          break;
        }
      }
      _selectedPreset ??= 'Custom';
    } else {
      _selectedPreset = 'Daily at 2 AM';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _cronController.dispose();
    _networkController.dispose();
    super.dispose();
  }

  void _onPresetChanged(String? preset) {
    if (preset == null) return;
    
    setState(() {
      _selectedPreset = preset;
      if (preset != 'Custom') {
        _cronController.text = _cronPresets[preset]!;
      }
    });
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _loading = true);

    try {
      if (widget.schedule == null) {
        // Create new schedule
        await _apiService.createSchedule(
          name: _nameController.text,
          cronExpression: _cronController.text,
          networkRange: _networkController.text,
          enabled: _enabled,
        );
      } else {
        // Update existing schedule
        await _apiService.updateSchedule(
          widget.schedule!.id,
          name: _nameController.text,
          cronExpression: _cronController.text,
          networkRange: _networkController.text,
          enabled: _enabled,
        );
      }

      if (mounted) {
        Navigator.pop(context, true);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.schedule == null
                ? 'Schedule created'
                : 'Schedule updated'),
          ),
        );
      }
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.schedule == null ? 'Create Schedule' : 'Edit Schedule'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Schedule Name',
                  hintText: 'e.g., Daily Network Scan',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a name';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _selectedPreset,
                decoration: const InputDecoration(
                  labelText: 'Schedule Frequency',
                  border: OutlineInputBorder(),
                ),
                items: _cronPresets.keys.map((String preset) {
                  return DropdownMenuItem<String>(
                    value: preset,
                    child: Text(preset),
                  );
                }).toList(),
                onChanged: _onPresetChanged,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _cronController,
                decoration: InputDecoration(
                  labelText: 'Cron Expression',
                  hintText: '0 2 * * *',
                  border: const OutlineInputBorder(),
                  helperText: _selectedPreset == 'Custom'
                      ? 'Format: minute hour day month day_of_week'
                      : null,
                ),
                enabled: _selectedPreset == 'Custom',
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a cron expression';
                  }
                  final parts = value.trim().split(' ');
                  if (parts.length != 5) {
                    return 'Cron expression must have 5 parts';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _networkController,
                decoration: const InputDecoration(
                  labelText: 'Network Range',
                  hintText: '192.168.1.0/24 or multiple: 192.168.1.0/24,10.0.0.0/24',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a network range';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              SwitchListTile(
                title: const Text('Enabled'),
                subtitle: const Text('Schedule will run automatically'),
                value: _enabled,
                onChanged: (value) {
                  setState(() => _enabled = value);
                },
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Icon(Icons.info_outline, size: 16, color: Colors.blue),
                        SizedBox(width: 8),
                        Text(
                          'Common Examples',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.blue,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '• */15 * * * * = Every 15 minutes\n'
                      '• 0 */6 * * * = Every 6 hours\n'
                      '• 0 2 * * * = Daily at 2 AM\n'
                      '• 0 9-17 * * 1-5 = Hourly, Mon-Fri 9AM-5PM',
                      style: const TextStyle(fontSize: 12, color: Colors.black87),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _loading ? null : _save,
          child: _loading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(widget.schedule == null ? 'Create' : 'Save'),
        ),
      ],
    );
  }
}
