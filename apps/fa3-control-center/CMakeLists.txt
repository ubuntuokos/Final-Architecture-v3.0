cmake_minimum_required(VERSION 3.24)
project(FA3ControlCenter VERSION 0.3.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2 QuickDialogs2 WebEngineQuick PrintSupport Network)

qt_standard_project_setup(REQUIRES 6.4)

qt_add_executable(fa3-control-center
    src/main.cpp
    src/Fa3RepositoryModel.cpp
    src/Fa3RepositoryModel.h
    src/JournalService.cpp
    src/JournalService.h
    src/PreferenceStore.cpp
    src/PreferenceStore.h
    src/SystemDeviceModel.cpp
    src/SystemDeviceModel.h
    src/ChatFileService.cpp
    src/ChatFileService.h
    src/ModelLibraryService.cpp
    src/ModelLibraryService.h
    src/McpControlService.cpp
    src/McpControlService.h
)

set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)
set_source_files_properties(qml/DashboardPage.qml PROPERTIES QT_RESOURCE_ALIAS DashboardPage.qml)
set_source_files_properties(qml/JournalPage.qml PROPERTIES QT_RESOURCE_ALIAS JournalPage.qml)
set_source_files_properties(qml/WebWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS WebWorkspace.qml)
set_source_files_properties(qml/ModelsProvidersPage.qml PROPERTIES QT_RESOURCE_ALIAS ModelsProvidersPage.qml)
set_source_files_properties(qml/AiStudioPage.qml PROPERTIES QT_RESOURCE_ALIAS AiStudioPage.qml)
set_source_files_properties(qml/SystemSettingsPage.qml PROPERTIES QT_RESOURCE_ALIAS SystemSettingsPage.qml)
set_source_files_properties(qml/RtdProvidersPage.qml PROPERTIES QT_RESOURCE_ALIAS RtdProvidersPage.qml)
set_source_files_properties(qml/ChatWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS ChatWorkspace.qml)
set_source_files_properties(qml/HelpBubble.qml PROPERTIES QT_RESOURCE_ALIAS HelpBubble.qml)
set_source_files_properties(qml/CheckpointManagerPage.qml PROPERTIES QT_RESOURCE_ALIAS CheckpointManagerPage.qml)
set_source_files_properties(qml/ExternalProvidersSetupPage.qml PROPERTIES QT_RESOURCE_ALIAS ExternalProvidersSetupPage.qml)
set_source_files_properties(qml/TokenControlCenterPage.qml PROPERTIES QT_RESOURCE_ALIAS TokenControlCenterPage.qml)
set_source_files_properties(qml/LanguageControlPage.qml PROPERTIES QT_RESOURCE_ALIAS LanguageControlPage.qml)
set_source_files_properties(qml/IntegrationsPage.qml PROPERTIES QT_RESOURCE_ALIAS IntegrationsPage.qml)

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
        qml/AiStudioPage.qml
        qml/SystemSettingsPage.qml
        qml/RtdProvidersPage.qml
        qml/ChatWorkspace.qml
        qml/HelpBubble.qml
        qml/CheckpointManagerPage.qml
        qml/ExternalProvidersSetupPage.qml
        qml/TokenControlCenterPage.qml
        qml/LanguageControlPage.qml
        qml/IntegrationsPage.qml
)

target_link_libraries(fa3-control-center
    PRIVATE
        Qt6::Quick
        Qt6::QuickControls2
        Qt6::QuickDialogs2
        Qt6::WebEngineQuick
        Qt6::PrintSupport
        Qt6::Network
)

install(TARGETS fa3-control-center
    RUNTIME DESTINATION libexec
)

install(FILES packaging/org.fa3.ControlCenter.desktop
    DESTINATION share/applications
)
