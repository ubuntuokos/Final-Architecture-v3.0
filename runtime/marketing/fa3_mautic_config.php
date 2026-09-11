<?php
$path = '/var/www/html/config/local.php';
if (!is_file($path)) {
    fwrite(STDERR, "Mautic local.php missing\n");
    exit(2);
}
$parameters = [];
require $path;
if (!is_array($parameters)) {
    fwrite(STDERR, "Mautic local.php did not define parameters\n");
    exit(3);
}
$parameters['api_enabled'] = true;
$parameters['api_enable_basic_auth'] = true;
$parameters['site_url'] = getenv('FA3_MAUTIC_SITE_URL') ?: 'http://127.0.0.1:8180';
$parameters['locale'] = 'hu';
$parameters['mailer_dsn'] = getenv('FA3_MAUTIC_MAILER_DSN') ?: 'smtp://smtp-sink:1025';
$out = "<?php\n\$parameters = " . var_export($parameters, true) . ";\n";
if (false === file_put_contents($path, $out)) {
    fwrite(STDERR, "Failed to update Mautic local.php\n");
    exit(4);
}
