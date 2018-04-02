#!/usr/bin/python
#
# Copyright (c) 2018 Excelero, Inc. All rights reserved.
#
# This Software is licensed under one of the following licenses:
#
# 1) under the terms of the "Common Public License 1.0" a copy of which is
#    available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/cpl.php.
#
# 2) under the terms of the "The BSD License" a copy of which is
#    available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/bsd-license.php.
#
# 3) under the terms of the "GNU General Public License (GPL) Version 2" a
#    copy of which is available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/gpl-license.php.
#
# Licensee has the right to choose one of the above licenses.
#
# Redistributions of source code must retain the above copyright
# notice and one of the license notices.
#
# Redistributions in binary form must reproduce both the above copyright
# notice, one of the license notices in the documentation
# and/or other materials provided with the distribution.
#
# Author:        Andreas Krause
# Version:       in development
# Maintainer:    Andreas Krause
# Email:         andreas@excelero.com

import argparse
import subprocess
from tempfile import TemporaryFile
import logging
import platform
import datetime
import re
from constants import *


# region command execution
def get_cmd_output(cmd_to_execute):
    with TemporaryFile() as t:
        try:
            logging.debug("Running Shell Command: " + cmd_to_execute)
            out = subprocess.check_output(cmd_to_execute, stderr=t, shell=True)
            logging.debug("Success")
            return 0, out
        except subprocess.CalledProcessError as e:
            t.seek(0)
            logging.error(t.read().strip("\n"))
            return e.returncode, cmd_to_execute, t.read()


def return_cmd_output(cmd):
    cmd_output = get_cmd_output(cmd)
    if cmd_output[0] == 0:
        return cmd_output[1]
    elif cmd_output[0] == 3:
        return 3, "Service not running."
    elif cmd_output[0] == 127:
        return print_yellow(cmd.strip().split(" ")[0] + " not found or not installed!")
    elif cmd_output[0] == 255:
        return print_yellow(cmd.strip().split(" ")[
                                0] + " shows no data as there is no IB transport layer. Looks like Ethernet "
                                     "connectivity.")
    elif cmd_output[0] != 0:
        return print_red("Error has occurred while executing " + cmd.strip().split(" ")[
            0] + "! Details can be found in the nvmesh_diag.log file.")


def run_cmd(cmd):
    cmd_output = get_cmd_output(cmd)
    if cmd_output[0] == 0:
        return print_green("Done. Successful.")
    elif cmd_output[0] == 127:
        return print_red("Error! " + cmd.strip().split(" ")[0] + " not found or not installed!")
    elif cmd_output[0] != 0:
        return print_red("Error has occurred while executing " + cmd.strip().split(" ")[
            0] + "! Details can be found in the nvmesh_diag.log file.")


def check_if_service_is_running(service):
    cmd_output = get_cmd_output(CMD_CHECK_IF_SERVICE_IS_RUNNING % service)
    if cmd_output[0] == 0:
        logging.debug("%s is running" % service)
        return True
    elif cmd_output[0] == 3:
        logging.debug("%s is not running" % service)
        return False
    else:
        return None
# endregion


# region output formatting
def print_and_log_info(text):
    logging.info(strip_tabs((text.lstrip("\n")).rstrip(":")))
    print('\033[1m' + '\033[4m' + text + '\033[0m')
    output.write(text + "\n")


def strip_tabs(text):
    text = text.replace("\t", "")
    return text


def print_green(text):
    logging.info(strip_tabs(text))
    output.write(text + "\n")
    return '\033[92m' + text + '\033[0m'


def print_yellow(text):
    logging.warning(strip_tabs(text))
    output.write(text + "\n")
    return '\033[33m' + text + '\033[0m'


def print_red(text):
    logging.error(text + "\n")
    output.write(text)
    return '\033[31m' + text + '\033[0m'
# endregion


# region Collecting Host Name Information
def get_hostname():
    output.write(host_name + "\n\n")
    if verbose_mode is True:
        print(host_name)
    print("Done.")
# endregion


# region Collecting Hardware Vendor and System Information
def get_hardware_information():
    if get_cmd_output(CMD_CHECK_FOR_DMIDECODE)[0] == 0:
        system_information = return_cmd_output(CMD_GET_SYSTEM_INFORMATION).split("\n")
        output.write(str(system_information[1].strip() + "\n" + system_information[2].strip() + "\n\n"))
        if verbose_mode is True:
            print system_information[1].strip(), system_information[2]
    else:
        print print_yellow("Couldn't collect hardware information!")
    print("Done.")
# endregion


def get_os_platform():
    linux_distributuion = platform.linux_distribution()[0].lower()

    if "suse" in linux_distributuion:
        return "sles"
    elif "red" in linux_distributuion:
        return "rhel"
    elif "centos" in linux_distributuion:
        return "rhel"
    else:
        return None


# region Collecting Operating System Information
def get_os_information():
    os_details = platform.linux_distribution()[0:2]
    kernel_version = str(platform.release())
    output.write(os_details[0] + os_details[1] + kernel_version + "\n\n")
    print os_details[0], os_details[
        1], kernel_version, "\nPlease verify this information with the latest support matrix!"
    print("Done.")
# endregion


# region Collecting and Verifying SELinux Information
def get_and_verify_selinux():
    if get_cmd_output(CMD_CHECK_FOR_SESTATUS)[0] == 0:
        selinux_status = return_cmd_output(CMD_GET_SETSTATUS).splitlines()
        for line in selinux_status:
            output.write(line + "\n")
        output.write("\n")
        if not selinux_status[0].split(":")[1].strip() == "disabled":
            print print_red("SELinux active. Should be disabled!")
            if set_parameters is True:
                if "y" in raw_input("Do you want to Disable SELinux now?[Yes/No]: ").lower():
                    print "Disabeling SELinux...\t", (run_cmd(CMD_DISABLE_SELINUX))
                else:
                    print("No it is. Going on...")
            if verbose_mode is True:
                for line in selinux_status:
                    print(line)
            print("\n")
        else:
            print print_green("Disabled - OK")
    else:
        print print_yellow("Couldn't find the SElinux policy tools, will try with 'getenforce' now.")
        if get_cmd_output(CMD_CHECK_FOR_GETENFORCE)[0] == 0:
            if "disabled" in return_cmd_output(CMD_SELINUX_GETENFORCE).lower():
                print print_green("Disabled - OK")
            else:
                if set_parameters is True:
                    if "y" in raw_input("Do you want to Disable SELinux now?[Yes/No]: ").lower():
                        print(run_cmd(CMD_DISABLE_SELINUX))
                    else:
                        print("No it is. Going on...")
        else:
            if "suse" in platform.linux_distribution()[0].lower():
                print print_yellow("Couldn't find any SElinux tools or config and the OS is SuSE, will check the"
                                   "AppArmor settings now!")
                if check_if_service_is_running("apparmor") is True:
                    apparmor_output = return_cmd_output(CMD_GET_APPARMOR_DETAILS)
                    output.write(apparmor_output + "\n")
                    print(print_yellow("AppArmor active!"))
                    if verbose_mode is True:
                        print apparmor_output
                    if set_parameters is True:
                        if "y" in raw_input("Do you want to disable and stop apparmor now?[Yes/No]: ").lower():
                            print "Stopping AppArmor services...\t", run_cmd(CMD_STOP_APPARMOR)
                            print "Disabling AppArmor services...\t", run_cmd(CMD_DISABLE_APPARMOR)
                            return
                        else:
                            print("No it is. Going on...")
                else:
                    print print_green("AppArmor not runnning - OK")
# endregion


# region Collecting and Verifying Firewall Information
def get_and_verify_firewall_suse():
    firewall_running = check_if_service_is_running("SuSEfirewall2")

    if firewall_running is True:
        print(print_yellow("Firewall active!"))
        if set_parameters is True:
            if "y" in raw_input("Do you want to disable the firewall now?[Yes/No]: ").lower():
                print "Stopping SuSEfirewall2...\t", run_cmd(CMD_STOP_SUSE_FIREWALL)
                print "Disabling SuSEfirewall2...\t", run_cmd(CMD_DISABLE_SUSE_FIREWALL)
                return
            else:
                print("No it is. Going on...")

    elif firewall_running is False:
        print print_green("Disabled - OK")
        return 3

    else:
        print print_red("Error: Couldn't verify firewalld!")
        return None
    return


def get_and_verify_firewall_rhel():
    firewall_running = check_if_service_is_running("firewalld")

    if firewall_running is True:
        iptables_output = return_cmd_output(CMD_GET_FIREWALL_CONFIG)
        output.write(iptables_output + "\n")
        print(print_yellow("Firewall active!"))

        if set_parameters is True:
            if "y" in raw_input("Do you want to disable the firewall now?[Yes/No]: ").lower():
                for command in CMD_DISABLE_FIREWALL:
                    print(run_cmd(command))
                return
            else:
                print("No it is. Going on...")

        if re.findall(r"%s dpt:%s" % (EXCELERO_MANAGEMENT_PORTS[0][0], EXCELERO_MANAGEMENT_PORTS[0][1]),
                      iptables_output) and re.findall(
            r"%s dpt:%s" % (EXCELERO_MANAGEMENT_PORTS[1][0], EXCELERO_MANAGEMENT_PORTS[1][1]), iptables_output):
            print print_green("For NVMesh Client operations OK. Excelero Management ports are configured.")
        else:
            print print_red(
                "Not OK for NVMesh client operations. Excelero Management ports tcp 4000 and tcp 4001 must be set and "
                "open!")
            if set_parameters is True:
                if "y" in raw_input("Do you want to open port 4000 and 4001 now?[Yes/No]: ").lower():
                    for command in CMD_SET_FIREWALL_FOR_NVMESH_MGMT:
                        print(run_cmd(command))
                else:
                    print("No it is. Going on...")

        if re.findall(r"%s dpt:%s" % (ROCEV2_TARGET_PORT[0], ROCEV2_TARGET_PORT[1]), iptables_output):
            print print_green("For NVMesh Target operations OK if the Link Layer is Ethernet. RoCEv2 ports are set.")
        else:
            print print_red(
                "Not OK for NVMesh Target operations if the Link Layer is Ethernet. RoCEv2 udp port 4791 must be set "
                "and open!")
            if set_parameters is True:
                if "y" in raw_input("Do you want to open port 4791 now?[Yes/No]: ").lower():
                    print(run_cmd(CMD_SET_FIREWALL_FOR_ROCEV2))
            else:
                print("No it is. Going on...")

        if re.findall(r"%s dpt:%s" % (MONGODB_PORT[0], MONGODB_PORT[1]), iptables_output):
            print print_green("For MongoDB HA operations OK. MongoDB ports are set.")
        else:
            print print_red("Not OK for MongoDB HA operations. MongoDB tcp port 27017 must be set and open!")
            if set_parameters is True:
                if "y" in raw_input("Do you want to open port 4791 now?[Yes/No]: ").lower():
                    print(run_cmd(CMD_SET_FIREWALL_FOR_MOGODB))
                else:
                    print("No it is. Going on...")
        if set_parameters is True:
            print "Reloading the firewall rules to apply changes.\n", run_cmd(CMD_RELOAD_FIREWALL_RULES)

    elif firewall_running is False:
        print print_green("Disabled - OK")
        return 3

    else:
        print print_red("Error: Couldn't verify firewalld!")
        return None


def get_and_verify_firewall():
    if os_platform == "rhel":
        get_and_verify_firewall_rhel()
        return
    elif os_platform == "sles":
        get_and_verify_firewall_suse()
        return
# endregion


# region Collecting and Verifying CPU Information
def get_and_verify_cpu():
    cpu_info = return_cmd_output("lscpu").split("\n")
    for line in cpu_info:
        output.write(line + "\n")
    output.write("\n")
    actual_cpu_frequency = None
    max_cpu_frequency = None
    for line in cpu_info:
        if "Socket(s)" in line:
            print line.split(":")[1].strip() + " Physical CPU"
        if "Model name" in line:
            print line.split(":")[1].lstrip()
        if "CPU MHz" in line:
            actual_cpu_frequency = float((line.split(":")[1]).strip())
            max_frequency_info = re.compile("\d+")
            for frequency in return_cmd_output("dmidecode -s processor-frequency").split("\n"):
                match = max_frequency_info.search(frequency)
                if match:
                    max_cpu_frequency = float(match.group(0))
    if actual_cpu_frequency and max_cpu_frequency is not None:
        if max_cpu_frequency - actual_cpu_frequency >= float(100):
            print print_yellow(
                "Actual running CPU frequency is lower than the maximum CPU frequency. This might impact performance! "
                "Check BIOS settings and verify System Tuning settings as below.\n")
        else:
            print print_green("CPU frequency settings OK.\n")
# endregion


def system_tuning_suse():
    if get_cmd_output(CMD_CHECK_FOR_TUNED_ADM)[0] != 0:

        print print_yellow("Tis seems to be a SuSE Linux server without Tuned installed and running. It's highly"
                           "recommended to install and configure Tuned for best performance results!")
        if set_parameters is True:
            if "y" in raw_input("Do you want to install and configure tuned now?[Yes/No]: ").lower():
                print "Installing Tuned ...\t", run_cmd(CMD_INSTALL_TUNED_SLES)
                print "Enabling the Tuned service...\t", run_cmd(CMD_ENABLE_TUNED)
                print "Starting the Tuned service...\t", run_cmd(CMD_START_TUNED)
                print "Setting and enabling the throughput-latency tuned policy...\t", run_cmd(CMD_SET_TUNED_PARAMETERS)
                return
            else:
                print("No it is. Going on...")
                return

    else:
        tuned_service_running = check_if_service_is_running("tuned")

        if tuned_service_running is False:
            print print_yellow("Tuned service is not running! Its hihgly recommended to run the Tuned service")
            if set_parameters is True:
                if "y" in raw_input("Do you want to start and enable the Tuned service now?[Yes/No] "):
                    print "Enabling the Tuned service...\t", run_cmd(CMD_ENABLE_TUNED)
                    print "Starting the Tuned service...\t", run_cmd(CMD_START_TUNED)
                else:
                    print("No it is. Going on...")
                    return

        tuned_adm_info = return_cmd_output(CMD_GET_TUNED_POLICY)
        output.write(tuned_adm_info + "\n")

        if "latency-performance" in tuned_adm_info:
            print(print_green("Tuned profile settings are OK"))
        else:
            print(print_yellow(
                "Tuned settings is not as recommended! Please run 'tuned-adm profile latency-performance' to set and "
                "enable the recommended Tuned profile and verify the Tuned service is running."))
            if set_parameters is True:
                if "y" in raw_input("Do you want to set the recommended tuned parameters now?[Yes/No]: ").lower():
                    print "Setting and enabling the throughput-latency tuned policy...\t", run_cmd(CMD_SET_TUNED_PARAMETERS)
                    return
                else:
                    print("No it is. Going on...")
                    return


def system_tuning_rhel():
    tuned_service_running = check_if_service_is_running("tuned")

    if tuned_service_running is False:
        print print_yellow("Tuned service is not running! Its hihgly recommended to run the Tuned service")
        if set_parameters is True:
            if "y" in raw_input("Do you want to start and enable the Tuned service now?[Yes/No] "):
                print "Enabling the Tuned service...\t", run_cmd(CMD_ENABLE_TUNED)
                print "Starting the Tuned service...\t", run_cmd(CMD_START_TUNED)
            else:
                print("No it is. Going on...")
                return

    tuned_adm_info = return_cmd_output(CMD_GET_TUNED_POLICY)
    output.write(tuned_adm_info + "\n")

    if "latency-performance" in tuned_adm_info:
        print(print_green("Tuned profile settings are OK"))
    else:
        print(print_yellow(
            "Tuned settings is not as recommended! Please run 'tuned-adm profile latency-performance' to set and "
            "enable the recommended Tuned profile and verify the Tuned service is running."))
        if set_parameters is True:
            if "y" in raw_input("Do you want to set the recommended tuned parameters now?[Yes/No]: ").lower():
                print "Setting and enabling the throughput-latency tuned policy...\t", run_cmd(CMD_SET_TUNED_PARAMETERS)
                return
            else:
                print("No it is. Going on...")
                return
    return


# region Collecting and Verifying System Tuning Information
def get_and_verify_system_tuning():

    if os_platform == "sles":
        system_tuning_suse()

    elif os_platform == "rhel":
        system_tuning_rhel()

    print("Checking the IRQ balancer...")
    irq_balance_running = check_if_service_is_running("irqbalance")

    if irq_balance_running is True:
        print print_green("The IRQ balancer is running - OK")

    elif irq_balance_running is False:
        print(print_yellow("The IRQ Balancer is not running. This might severely impact the system performance."))
        if set_parameters is True:
            if "y" in raw_input("Do you want to enable and start the IRQ Balance service now?[Yes/No]: "):
                    print "Enabling the IRQ balance service...\t", run_cmd(CMD_ENABALE_IRQ_BALANCER)
                    print "Starting the IRQ balance service...\t", run_cmd(CMD_START_IRQ_BALANCER)
            else:
                print("No it is. Going on...")

    return
# endregion


# region Collecting Memory Information
def get_memory_information():
    memory_info = return_cmd_output("free -h")
    output.write(memory_info + "\n")
    installed_memory = re.findall(REGEX_INSTALLED_MEMORY, memory_info)[0]
    if verbose_mode is True:
        print(installed_memory + " installed memory.\n")
    print("Done.")
# endregion


# region Collecting High Level Block Device Information
def get_block_device_information():
    lsblk_output = return_cmd_output("lsblk")
    output.write(lsblk_output + "\n")
    if verbose_mode is True:
        print(lsblk_output)
    print("Done.")
# endregion


def get_nvmesh_services():
    if get_cmd_output(CMD_GET_NVMESH_SERVICES)[0] == 0:
        nvmesh_services = return_cmd_output(CMD_GET_NVMESH_SERVICES).splitlines()
        if len(nvmesh_services) > 0:
            return nvmesh_services
    else:
        return None


def get_nvmesh_service_details(nvmesh_service):
    nvmesh_service_details = subprocess.Popen(CMD_GET_NVMESH_SERVICE_DETAILS % nvmesh_service, shell=True,
                                              stdout=subprocess.PIPE).stdout.read()
    if len(nvmesh_service_details) > 0:
        return nvmesh_service_details
    else:
        return None


# region Collecting NVMe Storage Configuration Information
def get_nvme_storage_info():
    nvmesh_services = get_nvmesh_services()
    if nvmesh_services is not None:
        print("Found that NVMesh software components are installed already. Checking the NVMesh services now...")
        for service in nvmesh_services:
            nvmesh_service_details = get_nvmesh_service_details(service.split(" ")[0]).strip()
            if "ok" in service.lower():
                print print_green(service)
                output.writelines(str(nvmesh_service_details))
                if verbose_mode is True:
                    print nvmesh_service_details
            else:
                print print_yellow(service)
                output.writelines(str(nvmesh_service_details))
                if verbose_mode is True:
                    print nvmesh_service_details
    else:
        if get_cmd_output(CMD_CHECK_FOR_NVME_CLI)[0] == 0:
            nvme_list_output = return_cmd_output(CMD_GET_NVME_SSD).splitlines()
            if os_platform == "sles":
                if len(nvme_list_output) > 2:
                    for line in nvme_list_output:
                        output.write(line + "\n")
                    if verbose_mode is True:
                        for line in nvme_list_output:
                            print(line)
                else:
                    print print_yellow("No NVMe SSD found on this server! This server can only be configured as a NVMesh "
                                           "Client.")
            else:
                nvme_numa_output = return_cmd_output(CMD_GET_NVME_SDD_NUMA)
                if len(nvme_numa_output) > 0:
                    if verbose_mode is True:
                        for line in nvme_list_output:
                            print(line)
                        print("\n" + nvme_numa_output)
                        output.write("\n" + nvme_numa_output + "\n")
                        for line in nvme_list_output:
                            output.write(line + "\n")
            print("Done.")
            return
        else:
            print print_yellow("The nvme-cli tools seem to be missing!")
            if set_parameters is True:
                if "y" in raw_input("Do you want to install the nvme-cli?[Yes/No]: ").lower():
                    if "suse" in (platform.linux_distribution()[0]).lower():
                        print "Installing nvme-cli ...\t", run_cmd(CMD_INSTALL_NVME_CLI_SLES)
                    else:
                        print "Installing nvme-cli ...\t", run_cmd(CMD_INSTALL_NVME_CLI_RHEL)
                    return get_nvme_storage_info()
                else:
                    print("No it is. Going on...")
                    return

    print("Done.")
# endregion


# region Collecting And Verifying R-NIC Information
def get_and_verfy_rnic_conf():
    rnics_output = return_cmd_output(CMD_GET_RNIC_INFO)
    output.write("\n" + rnics_output + "\n")
    rnics = rnics_output.split("\n\n")
    for rnic in rnics:
        max_rnic_speed_and_pcie_width = re.findall(REGEX_HCA_MAX, rnic)
        actual_rnic_speed_and_pcie_with = re.findall(REGEX_HCA_ACTUAL, rnic)
        rnic_details = rnic.splitlines()
        if len(rnic_details) > 0:
            print("Checking HCA at PCIe address: " + rnic_details[0])
            print("\tVendor/OEM information:" + rnic_details[2].split("Device")[0])
            try:
                if "Product Name" in rnic_details[8]:
                    print "\tHCA Type: " + rnic_details[8].split(":")[1]
            except:
                pass
            print("\tFirmware level: " + rnic_details[1].split(":")[1].strip())

            if max_rnic_speed_and_pcie_width[0][0] == actual_rnic_speed_and_pcie_with[0][0]:
                print print_green("\tHCA PCIe speed settings OK. Running at " + actual_rnic_speed_and_pcie_with[0][0])
            else:
                print print_yellow("\tThe HCA is capable of ") + max_rnic_speed_and_pcie_width[0][
                    0] + " but its running at " + actual_rnic_speed_and_pcie_with[0][
                          0] + "! Check BIOS and HW settings to ensure max performance and a stable environment!"
            if max_rnic_speed_and_pcie_width[0][1] == actual_rnic_speed_and_pcie_with[0][1]:
                print print_green(
                    "\tHCA PCIe width settings OK. Running at " + actual_rnic_speed_and_pcie_with[0][1]) + "\n"
            else:
                print print_yellow("\tThe HCA is capable of ") + max_rnic_speed_and_pcie_width[0][
                    1] + " but its running at " + actual_rnic_speed_and_pcie_with[0][
                          0] + "! Check BIOS and HW settings to ensure max performance and a stable environment!\n"
# endregion


def check_for_inbox_driver_packages(driver_packages):
    missing_inbox_drivers = []
    for rpm_package in driver_packages:
        if "Error" in return_cmd_output(CMD_CHECK_RPM % rpm_package):
            missing_inbox_drivers.append(rpm_package)
            output.write("missing " + rpm_package + "!")
            print print_red("\t%s missing " % rpm_package + "!")
    if len(missing_inbox_drivers) != 0:
        return missing_inbox_drivers
    else:
        print print_green("Inbox drivers installed - OK ")
        return missing_inbox_drivers


# region Collecting And Verifying Mellanox Driver Information
def get_ofed_information():
    ofed_version = return_cmd_output(CMD_GET_OFED_INFO)
    output.write("OFED: " + ofed_version + "\n")
    if "not found or not installed" in ofed_version:
        print "OFED not installed! Checking for inbox drivers now."
        if os_platform == "sles":
            missing_inbox_drivers = check_for_inbox_driver_packages(SLES_INBOX_DRIVERS)
            if len(missing_inbox_drivers) != 0:
                print print_red("OFED is not installed and Inbox drivers are missing! \n"
                                "You must install either OFED or the missing Inbox drivers!\n")
                if set_parameters is True:
                    if "y" in raw_input("Do you want to install the Mellanox inbox drivers now?[Yes/No]: "):
                        for package in missing_inbox_drivers:
                            print "Installing package %s ...\t" % package, run_cmd(CMD_INSTALL_SLES_PACKAGE % package)
                        return
                    else:
                        print("No it is. Going on...")
                        return
        elif os_platform == "rhel":
            missing_inbox_drivers = check_for_inbox_driver_packages(RHEL_INBOX_DRIVERS)
            if len(missing_inbox_drivers) != 0:
                print print_red("OFED is not installed and Inbox drivers are missing! \n"
                                "You must install either OFED or the missing Inbox drivers!\n")
                if set_parameters is True:
                    if "y" in raw_input("Do you want to install the Mellanox inbox drivers now?[Yes/No]: "):
                        for package in missing_inbox_drivers:
                            print "Installing package %s ...\t" % package, run_cmd(CMD_INSTALL_RHEL_PACKAGE)
                    else:
                        print("No it is. Going on...")
                        return
    else:
        print print_green("OFED installed - OK "), "\nVersion: " + ofed_version + "Please verify this information " \
                                                                                  "with the latest support matrix!"
    return
# endregion


# region Collecting and Verifying RDMA HCA Information
def get_and_veryfy_rdma_conf():
    if get_cmd_output(CMD_GET_OFED_INFO)[0] == 0:
        ibv_devinfo_output = return_cmd_output(CMD_GET_IBV_DEVINFO)
        output.write(ibv_devinfo_output + "\n")
        hca_list = re.findall(REGEX_HCA_LIST, ibv_devinfo_output, re.MULTILINE)
        for (hca, guid1, guid2, guid3, guid4) in hca_list:
            if guid1 == "0000":
                print print_red(hca + " guid information seems incorrect or missing. Please check!")
            else:
                print print_green(hca + " guid OK")
            one_qp_per_recovery = re.sub("\s\s+", " ", (return_cmd_output(CMD_GET_ONE_QP % hca).lstrip(" ")))
            if "True" in one_qp_per_recovery:
                print print_green(hca + " ready and configured for RDDA")
            elif "False" in one_qp_per_recovery:
                print print_yellow(
                    hca + " will support RDDA but is not configured correctly. You have to enable ONE_QP_PER_RECOVERY in "
                          "the Mellanox firmware if you want to use RDDA")
            elif "-E-" in one_qp_per_recovery:
                print print_red(
                    hca + " will not support RDDA due to firmware limitations on the HCA. If you intent to use RDDA, you "
                          "have to update the firmware and enable ONE_QP_PER_RECOVERY on the HCA.")
        if verbose_mode is True:
            print(return_cmd_output(CMD_GET_IBDEV2NETDEV))
    else:
        print print_yellow("OFED is not installed! Skipping the R-NIC settings check.")
    print("Done.")
    return 0
# endregion


# region Collect Infiniband Environment Specific Information
def get_ib_info():
    if get_cmd_output(CMD_GET_OFED_INFO)[0] != 0:
        print print_yellow("OFED is not installed! Skipping the IB environment check.")
    else:
        output.write(return_cmd_output(CMD_GET_IBHOSTS) + "\n" + return_cmd_output(CMD_GET_IBSWITCHES) + "\n")
        if verbose_mode is True:
            print return_cmd_output(CMD_GET_IBHOSTS), "\n" + return_cmd_output(CMD_GET_IBSWITCHES)
    print("Done.")
    return 0
# endregion


# region Collect IP Address Information
def get_ip_info():
    output.write(return_cmd_output(CMD_GET_IP_INFO))
    if verbose_mode is True:
        print return_cmd_output(CMD_GET_IP_INFO)
    print("Done.")
# endregion


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode',
                        help='Please specify the run mode. Either preinstall, healthcheck or full. Usage nvmeshdiag '
                             '-m/--mode [preinstall|healthcheck|full]', required=False)
    parser.add_argument('-v', '--verbose', type=bool, nargs='?', const=True, default=False,
                        help="Activate verbose output mode.")
    parser.add_argument('-s', '--set-parameters', type=bool, nargs='?', const=True, default=False,
                        help="Set the recommended parameters where possible.")
    args = parser.parse_args()
    exec_mode = getattr(args, "mode")
    verbose_mode = getattr(args, "verbose")
    set_parameters = getattr(args, "set_parameters")

    host_name = platform.node()
    output = open(host_name + '_' + str(datetime.datetime.utcnow()).replace(" ", "_") + '_nvmesh_diag_output.txt', 'w')

    logging.basicConfig(filename='nvmesh_diag.log', format='%(asctime)s\t%(levelname)s\t%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.debug(
        "Execution Started -------------------------------------------------------------------------------------")
    logging.debug("Execution mode: " + unicode(exec_mode))
    logging.debug("Verbose output enabled: " + unicode(verbose_mode))
    logging.debug("Setting recommended parameters: " + unicode(set_parameters))
    logging.debug("Storing output to: " + output.name)

    os_platform = get_os_platform()
    if os_platform is None:
        print print_red("Error: OS platform not supported!")
        exit()
    else:
        logging.debug("OS platform: %s" % os_platform)

    print_and_log_info("Collecting Host Name Information:")
    get_hostname()
    print_and_log_info("\nCollecting Hardware Vendor and System Information:")
    get_hardware_information()
    print_and_log_info("\nCollecting Operating System Information:")
    get_os_information()
    print_and_log_info("\nCollecting and Verifying SELinux Information:")
    get_and_verify_selinux()
    print_and_log_info("\nCollecting and Verifying Firewall Information:")
    get_and_verify_firewall()
    print_and_log_info("\nCollecting and Verifying CPU Information:")
    get_and_verify_cpu()
    print_and_log_info("Collecting and Verifying System Tuning Information:")
    get_and_verify_system_tuning()
    print_and_log_info("\nCollecting Memory Information:")
    get_memory_information()
    print_and_log_info("\nCollecting High Level Block Device Information:")
    get_block_device_information()
    print_and_log_info("\nCollecting NVMe Storage Device Information:")
    get_nvme_storage_info()
    print_and_log_info("\nCollecting And Verifying Mellanox Driver Information:")
    get_ofed_information()
    print_and_log_info("\nCollecting and Verifying R-NIC information:")
    get_and_verfy_rnic_conf()
    print_and_log_info("\nCollecting And Verifying RDMA Specific Information:")
    get_and_veryfy_rdma_conf()
    print_and_log_info("\nCollecting Infiniband Specific Information:")
    get_ib_info()
    print_and_log_info("\nCollecting IP Address Information:")
    get_ip_info()

