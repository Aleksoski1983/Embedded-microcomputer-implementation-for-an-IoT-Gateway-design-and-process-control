# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
cmake_minimum_required(VERSION 3.13)
set(PICO_BOARD pico_w)

# Comment out Perl requirement
# find_package(Perl)
# if(NOT PERL_FOUND)
#     message(FATAL_ERROR "Perl is needed for generating the fsdata.c file")
# endif()


include(pico_sdk_import.cmake)
project(wifi_configure_project C CXX ASM)

set(PROGRAM_NAME wifi_configure)
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

add_compile_options(
    -Wall
    -Werror
    -Wno-main
)

# Generate wifi_setup/my_fsdata.c from wifi_setup/fs using Python (no Perl required).
find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    message(STATUS "Generating my_fsdata.c using wifi_setup/generate_fsdata.py")
    execute_process(
        COMMAND ${Python3_EXECUTABLE} generate_fsdata.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/wifi_setup
        ECHO_OUTPUT_VARIABLE
        ECHO_ERROR_VARIABLE
    )
else()
    message(STATUS "Python3 not found. Using existing wifi_setup/my_fsdata.c")
endif()

# initialize the Raspberry Pi Pico SDK
pico_sdk_init()

add_executable(${PROGRAM_NAME}
    main.c
    tcp_test_server.c
    api_server.c
    ssd1306.c
    dht22.c
    mqtt_client.c
    wifi_setup/access_point.c
    wifi_setup/http_server.c
    wifi_setup/flash_program.c
    wifi_setup/dhcp_server.c
)

target_include_directories(${PROGRAM_NAME} PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/.
    ${CMAKE_CURRENT_LIST_DIR}/wifi_setup
)
target_link_libraries(${PROGRAM_NAME}
    pico_cyw43_arch_lwip_threadsafe_background
    pico_lwip_http
    pico_lwip_mqtt
    hardware_flash
    hardware_i2c
    pico_stdlib
)

pico_enable_stdio_usb(${PROGRAM_NAME} TRUE)
pico_enable_stdio_uart(${PROGRAM_NAME} TRUE)
suppress_tinyusb_warnings()

pico_add_extra_outputs(${PROGRAM_NAME})

