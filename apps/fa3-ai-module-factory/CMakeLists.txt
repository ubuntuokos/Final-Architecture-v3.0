# SPDX-License-Identifier: Apache-2.0
cmake_minimum_required(VERSION 3.24)
project(FA3AIModuleFactory VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Core Gui Quick QuickControls2 Test)
qt_standard_project_setup(REQUIRES 6.4)

qt_add_executable(fa3-ai-module-factory
    src/main.cpp
    src/AIModuleFactoryService.cpp
    src/AIModuleFactoryService.h
)

set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)
qt_add_qml_module(fa3-ai-module-factory
    URI FA3.AIModuleFactory
    VERSION 1.0
    RESOURCE_PREFIX "/qt/qml"
    QML_FILES qml/Main.qml
)

target_link_libraries(fa3-ai-module-factory PRIVATE
    Qt6::Core Qt6::Gui Qt6::Quick Qt6::QuickControls2
)

enable_testing()
qt_add_executable(fa3-ai-module-factory-test
    tests/test_service.cpp
    src/AIModuleFactoryService.cpp
    src/AIModuleFactoryService.h
)
target_include_directories(fa3-ai-module-factory-test PRIVATE src)
target_link_libraries(fa3-ai-module-factory-test PRIVATE Qt6::Core Qt6::Test)
add_test(NAME fa3-ai-module-factory-test COMMAND fa3-ai-module-factory-test)

install(TARGETS fa3-ai-module-factory RUNTIME DESTINATION libexec)
install(FILES packaging/org.fa3.AIModuleFactory.desktop DESTINATION share/applications)
