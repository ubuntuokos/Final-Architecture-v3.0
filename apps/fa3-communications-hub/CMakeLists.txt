cmake_minimum_required(VERSION 3.24)
project(FA3CommunicationsHub VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2)
qt_standard_project_setup(REQUIRES 6.4)

qt_add_executable(fa3-communications-hub
    src/main.cpp
)

set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)
set_source_files_properties(qml/CommunicationsSurface.qml PROPERTIES QT_RESOURCE_ALIAS CommunicationsSurface.qml)

qt_add_qml_module(fa3-communications-hub
    URI FA3.CommunicationsHub
    VERSION 1.0
    RESOURCE_PREFIX "/qt/qml"
    QML_FILES
        qml/Main.qml
        qml/CommunicationsSurface.qml
)

target_link_libraries(fa3-communications-hub PRIVATE Qt6::Quick Qt6::QuickControls2)

install(TARGETS fa3-communications-hub RUNTIME DESTINATION libexec)
install(FILES packaging/org.fa3.CommunicationsHub.desktop DESTINATION share/applications)
