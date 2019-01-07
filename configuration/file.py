import configparser


def get_param_from_file(file, section, param):

    config = configparser.ConfigParser()

    try:
        config.read(file)
    except configparser.Error as err:
        print("Error loading config file: {0}".format(err))
        exit(1)

    if section in config:

        try:
            param_value = config.get(section, param)

            return param_value
        except configparser.NoOptionError as err:
            print("Option not found in config file: {0}".format(err))

    else:
        print('Motion configuration not present in file')
