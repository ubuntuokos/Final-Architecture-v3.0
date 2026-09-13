cmake_minimum_required(VERSION 3.24)
project(FA3ControlCenter VERSION 0.4.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2 Widgets WebEngineQuick)

qt_standard_project_setup(REQUIRES 6.4)

qt_add_executable(fa3-control-center
    src/main.cpp
    src/Fa3RepositoryModel.cpp
    src/Fa3RepositoryModel.h
    src/SettingsStore.cpp
    src/SettingsStore.h
)

set_source_files_properties(qml/AppShell.qml PROPERTIES QT_RESOURCE_ALIAS AppShell.qml)
set_source_files_properties(qml/LanguageAwareAppShell.qml PROPERTIES QT_RESOURCE_ALIAS LanguageAwareAppShell.qml)
set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)
set_source_files_properties(qml/SettingsPage.qml PROPERTIES QT_RESOURCE_ALIAS SettingsPage.qml)
set_source_files_properties(qml/MentorPage.qml PROPERTIES QT_RESOURCE_ALIAS MentorPage.qml)
set_source_files_properties(qml/CoachPage.qml PROPERTIES QT_RESOURCE_ALIAS CoachPage.qml)
set_source_files_properties(qml/ManagerPage.qml PROPERTIES QT_RESOURCE_ALIAS ManagerPage.qml)
set_source_files_properties(qml/ModelManagerPage.qml PROPERTIES QT_RESOURCE_ALIAS ModelManagerPage.qml)
set_source_files_properties(qml/LanguageControlPage.qml PROPERTIES QT_RESOURCE_ALIAS LanguageControlPage.qml)
set_source_files_properties(qml/AnimationIntegrationPanel.qml PROPERTIES QT_RESOURCE_ALIAS AnimationIntegrationPanel.qml)
set_source_files_properties(qml/SystemPage.qml PROPERTIES QT_RESOURCE_ALIAS SystemPage.qml)
set_source_files_properties(qml/EmbeddedAppsPage.qml PROPERTIES QT_RESOURCE_ALIAS EmbeddedAppsPage.qml)

qt_add_qml_module(fa3-control-center
    URI FA3.ControlCenter
    VERSION 1.0
    RESOURCE_PREFIX "/qt/qml"
    QML_FILES
        qml/AppShell.qml
        qml/LanguageAwareAppShell.qml
        qml/Main.qml
        qml/SettingsPage.qml
        qml/MentorPage.qml
        qml/CoachPage.qml
        qml/ManagerPage.qml
        qml/ModelManagerPage.qml
        qml/LanguageControlPage.qml
        qml/AnimationIntegrationPanel.qml
        qml/SystemPage.qml
        qml/EmbeddedAppsPage.qml
)

target_link_libraries(fa3-control-center
    PRIVATE
        Qt6::Quick
        Qt6::QuickControls2
        Qt6::Widgets
        Qt6::WebEngineQuick
)

install(TARGETS fa3-control-center
    RUNTIME DESTINATION libexec
)

install(FILES packaging/org.fa3.ControlCenter.desktop
    DESTINATION share/applications
)
