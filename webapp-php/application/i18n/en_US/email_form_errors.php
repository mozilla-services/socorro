<?php
/**
  * Strings for the form on /admin/email
  *
  * PHP Version 5
  * 
  * @category Admin
  * @package  Admin.Email
  * @author   Ozten <ozten@mozilla.com>
  * @license  MPL/GPL/LGPL http://www.mozilla.org/MPL/
  * @link     http://code.google.com/p/socorro/
  *
  */
$lang = array(
    'email_signature' => array(
        'required' => 'Exact Signature is required',
        'length' => 'Exact Signature must be between 2 and 1024 characters',
    ),
    'email_subject' => array(
        'required' => 'Subject is required',
        'length' => 'Subject must be less than 140 characters',
    ),
    'email_body' => array(
        'required' => "Email Body is required",
        'length' => 'Email Body must be less than 8014 characters',
        'valid_unknown_variable' => 'You have mis-typed a variable name. Unknown email variable',
        'valid_no_unsubscribe' => "The email body doesn't contain an un-subscribe from this email url variable. This is required.",
    ),
    'email_start_date' => array(
        'required' => 'An Start Date is required',
        'length' => 'An Start Datsce must be exactly 10 characters',
        'valid_date' => 'An Start Date must be in the format dd/mm/yyyy',
    ),
    'email_end_date' => array(
        'required' => 'An End Date is required',
        'length' => 'An End Date must be exactly 10 characters',
        'valid_date' => 'An End Date must be in the format dd/mm/yyyy',
    ),
);

?>