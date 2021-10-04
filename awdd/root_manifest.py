from awdd.manifest import *


def create_root_manifest() -> ManifestObjectDefinition:
    root = ManifestObjectDefinition(0x00) # TODO - this is prob not 00
    timestamp = ManifestProperty(root)
    timestamp.name = "timestamp"
    timestamp.type = PropertyType.INTEGER
    timestamp.integer_format = IntegerFormat.TIMESTAMP
    timestamp.index = 0x08
    root.properties.append(timestamp)

    is_anonymous = ManifestProperty(root)
    is_anonymous.name = "isAnonymous"
    is_anonymous.index = 0x20
    is_anonymous.type = PropertyType.BOOLEAN
    root.properties.append(is_anonymous)

    device_config_id = ManifestProperty(root)
    device_config_id.name = "deviceConfigId"
    device_config_id.index = 0x28
    device_config_id.type = PropertyType.INTEGER
    root.properties.append(device_config_id)

    tz_offset = ManifestProperty(root)
    tz_offset.name = "tz_offset"
    tz_offset.index = 0x2D
    tz_offset.type = PropertyType.INTEGER_64
    root.properties.append(tz_offset)

    investigation_id = ManifestProperty(root)
    investigation_id.name = "investigationId"
    investigation_id.index = 0x30
    investigation_id.type = PropertyType.INTEGER
    root.properties.append(investigation_id)

    build_type = ManifestProperty(root)
    build_type.name = "buildtype"
    build_type.index = 0x31
    build_type.type = PropertyType.STRING_UNICODE
    root.properties.append(build_type)

    model = ManifestProperty(root)
    model.name = "model"
    model.index = 0x3A
    model.type = PropertyType.STRING_UNICODE
    root.properties.append(model)

    software_build = ManifestProperty(root)
    software_build.name = "softwareBuild"
    software_build.index = 0x42
    software_build.type = PropertyType.STRING_UNICODE
    root.properties.append(software_build)

    firmware_version = ManifestProperty(root)
    firmware_version.name = "firmwareVersion"
    firmware_version.index = 0x4A
    firmware_version.type = PropertyType.STRING_UNICODE
    root.properties.append(firmware_version)

    metric_file_type = ManifestProperty(root)
    metric_file_type.name = "metric_file_type"
    metric_file_type.index = 0x68
    metric_file_type.type = PropertyType.INTEGER
    root.properties.append(metric_file_type)

    metricslog = ManifestObjectDefinition(0x7A)

    trigger_time = ManifestProperty(metricslog)
    trigger_time.name = "triggerTime"
    trigger_time.index = 0x20
    trigger_time.type = PropertyType.INTEGER
    trigger_time.integer_format = IntegerFormat.TIMESTAMP
    metricslog.properties.append(trigger_time)

    trigger_id = ManifestProperty(metricslog)
    trigger_id.name = "triggerId"
    trigger_id.index = 0x28
    trigger_id.type = PropertyType.INTEGER
    metricslog.properties.append(trigger_id)

    profile_id = ManifestProperty(metricslog)
    profile_id.name = "profileId"
    profile_id.type = PropertyType.INTEGER
    profile_id.index = 0x30
    metricslog.properties.append(profile_id)

    metricslogs = ManifestProperty(root)
    metricslogs.name = "metricslogs"
    metricslogs.index = 0x7A
    metricslogs.type = PropertyType.OBJECT
    root.properties.append(metricslogs)

    return root