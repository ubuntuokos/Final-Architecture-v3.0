cmake_minimum_required(VERSION 3.24)
project(FA3ControlCenter VERSION 0.3.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2 QuickDialogs2 WebEngineQuick PrintSupport Network DBus)

qt_standard_project_setup(REQUIRES 6.4)

qt_add_executable(fa3-control-center
    src/main.cpp
    src/AppCatalogService.cpp
    src/AppCatalogService.h
    src/ChatFileService.cpp
    src/ChatFileService.h
    src/DecisionFabricService.cpp
    src/DecisionFabricService.h
    src/ExternalLlmCatalogModel.cpp
    src/ExternalLlmCatalogModel.h
    src/Fa3RepositoryModel.cpp
    src/Fa3RepositoryModel.h
    src/JournalService.cpp
    src/JournalService.h
    src/ModelLibraryService.cpp
    src/ModelLibraryService.h
    src/McpControlService.cpp
    src/McpControlService.h
    src/McpGatewayService.cpp
    src/McpGatewayService.h
    src/PreferenceStore.cpp
    src/PreferenceStore.h
    src/SessionVaultService.cpp
    src/SessionVaultService.h
    src/SystemDeviceModel.cpp
    src/SystemDeviceModel.h
)

set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)
set_source_files_properties(qml/DashboardPage.qml PROPERTIES QT_RESOURCE_ALIAS DashboardPage.qml)
set_source_files_properties(qml/JournalPage.qml PROPERTIES QT_RESOURCE_ALIAS JournalPage.qml)
set_source_files_properties(qml/WebWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS WebWorkspace.qml)
set_source_files_properties(qml/ModelsProvidersPage.qml PROPERTIES QT_RESOURCE_ALIAS ModelsProvidersPage.qml)
set_source_files_properties(qml/ProviderExplorerView.qml PROPERTIES QT_RESOURCE_ALIAS ProviderExplorerView.qml)
set_source_files_properties(qml/ProviderExecutionView.qml PROPERTIES QT_RESOURCE_ALIAS ProviderExecutionView.qml)
set_source_files_properties(qml/AiStudioPage.qml PROPERTIES QT_RESOURCE_ALIAS AiStudioPage.qml)
set_source_files_properties(qml/SubtitleStudioPage.qml PROPERTIES QT_RESOURCE_ALIAS SubtitleStudioPage.qml)
set_source_files_properties(qml/NarrationStudioPage.qml PROPERTIES QT_RESOURCE_ALIAS NarrationStudioPage.qml)
set_source_files_properties(qml/SystemSettingsPage.qml PROPERTIES QT_RESOURCE_ALIAS SystemSettingsPage.qml)
set_source_files_properties(qml/RtdProvidersPage.qml PROPERTIES QT_RESOURCE_ALIAS RtdProvidersPage.qml)
set_source_files_properties(qml/ChatWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS ChatWorkspace.qml)
set_source_files_properties(qml/HelpBubble.qml PROPERTIES QT_RESOURCE_ALIAS HelpBubble.qml)
set_source_files_properties(qml/CheckpointManagerPage.qml PROPERTIES QT_RESOURCE_ALIAS CheckpointManagerPage.qml)
set_source_files_properties(qml/ExternalProvidersSetupPage.qml PROPERTIES QT_RESOURCE_ALIAS ExternalProvidersSetupPage.qml)
set_source_files_properties(qml/TokenControlCenterPage.qml PROPERTIES QT_RESOURCE_ALIAS TokenControlCenterPage.qml)
set_source_files_properties(qml/LanguageControlPage.qml PROPERTIES QT_RESOURCE_ALIAS LanguageControlPage.qml)
set_source_files_properties(qml/IntegrationsPage.qml PROPERTIES QT_RESOURCE_ALIAS IntegrationsPage.qml)
set_source_files_properties(qml/AcceleratorGuardPage.qml PROPERTIES QT_RESOURCE_ALIAS AcceleratorGuardPage.qml)
set_source_files_properties(qml/Fa3OsPage.qml PROPERTIES QT_RESOURCE_ALIAS Fa3OsPage.qml)
set_source_files_properties(qml/WorkManagementPage.qml PROPERTIES QT_RESOURCE_ALIAS WorkManagementPage.qml)
set_source_files_properties(qml/McpGatewayPage.qml PROPERTIES QT_RESOURCE_ALIAS McpGatewayPage.qml)
set_source_files_properties(qml/KnowledgePage.qml PROPERTIES QT_RESOURCE_ALIAS KnowledgePage.qml)
set_source_files_properties(qml/TrustCertificatesPage.qml PROPERTIES QT_RESOURCE_ALIAS TrustCertificatesPage.qml)
set_source_files_properties(qml/SessionVaultPage.qml PROPERTIES QT_RESOURCE_ALIAS SessionVaultPage.qml)
set_source_files_properties(qml/DecisionFabricPage.qml PROPERTIES QT_RESOURCE_ALIAS DecisionFabricPage.qml)
set_source_files_properties(qml/DecisionInspectorPage.qml PROPERTIES QT_RESOURCE_ALIAS DecisionInspectorPage.qml)
set_source_files_properties(qml/ProjectRadarPage.qml PROPERTIES QT_RESOURCE_ALIAS ProjectRadarPage.qml)
set_source_files_properties(qml/ContextInspectorPage.qml PROPERTIES QT_RESOURCE_ALIAS ContextInspectorPage.qml)
set_source_files_properties(qml/AgentActionCenterPage.qml PROPERTIES QT_RESOURCE_ALIAS AgentActionCenterPage.qml)
set_source_files_properties(qml/UpdateCenterPage.qml PROPERTIES QT_RESOURCE_ALIAS UpdateCenterPage.qml)

qt_add_qml_module(fa3-control-center
    URI FA3.ControlCenter
    VERSION 1.0
    RESOURCE_PREFIX "/qt/qml"
    QML_FILES
        qml/Main.qml
        qml/DashboardPage.qml
        qml/JournalPage.qml
        qml/WebWorkspace.qml
        qml/ModelsProvidersPage.qml
        qml/ProviderExplorerView.qml
        qml/ProviderExecutionView.qml
        qml/AiStudioPage.qml
        qml/SubtitleStudioPage.qml
        qml/NarrationStudioPage.qml
        qml/SystemSettingsPage.qml
        qml/RtdProvidersPage.qml
        qml/ChatWorkspace.qml
        qml/HelpBubble.qml
        qml/CheckpointManagerPage.qml
        qml/ExternalProvidersSetupPage.qml
        qml/TokenControlCenterPage.qml
        qml/LanguageControlPage.qml
        qml/IntegrationsPage.qml
        qml/AcceleratorGuardPage.qml
        qml/Fa3OsPage.qml
        qml/WorkManagementPage.qml
        qml/McpGatewayPage.qml
        qml/KnowledgePage.qml
        qml/TrustCertificatesPage.qml
        qml/SessionVaultPage.qml
        qml/DecisionFabricPage.qml
        qml/DecisionInspectorPage.qml
        qml/ProjectRadarPage.qml
        qml/ContextInspectorPage.qml
        qml/AgentActionCenterPage.qml
        qml/UpdateCenterPage.qml
)

qt_add_resources(fa3-control-center "fa3_canonical_app_catalog"
    PREFIX "/fa3/canonical"
    BASE "${CMAKE_CURRENT_SOURCE_DIR}/../../canonical"
    FILES
        "${CMAKE_CURRENT_SOURCE_DIR}/../../canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"
)

target_link_libraries(fa3-control-center
    PRIVATE
        Qt6::Quick
        Qt6::QuickControls2
        Qt6::QuickDialogs2
        Qt6::WebEngineQuick
        Qt6::PrintSupport
        Qt6::Network
        Qt6::DBus
)

install(TARGETS fa3-control-center
    RUNTIME DESTINATION libexec
)

install(PROGRAMS
    "${CMAKE_CURRENT_SOURCE_DIR}/../../scripts/fa3-app-provisioner.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../bin/fa3-session-vault-init"
    DESTINATION libexec
)

install(FILES
    "${CMAKE_CURRENT_SOURCE_DIR}/../../canonical/FA3-APP-LIFECYCLE-001.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../canonical/FA3-APP-REQUEST-001.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"
    DESTINATION share/fa3/canonical
)

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../deployment/app-providers/"
    DESTINATION share/fa3/app-providers
    FILES_MATCHING PATTERN "*.json"
)

install(FILES packaging/org.fa3.ControlCenter.desktop
    DESTINATION share/applications
)
