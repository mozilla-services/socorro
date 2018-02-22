# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.cron.crontabber_app import jobs_converter, DEFAULT_JOBS


class TestJobsConverter:
    expected_job_names = [
        'ADUCronApp',
        'BugzillaCronApp',
        'BuildADUCronApp',
        'CleanRawADICronApp',
        'DropOldPartitionsCronApp',
        'DuplicatesCronApp',
        'ElasticsearchCleanupCronApp',
        'FTPScraperCronApp',
        'FeaturedVersionsAutomaticCronApp',
        'GraphicsDeviceCronApp',
        'ProductVersionsCronApp',
        'ReportsCleanCronApp',
        'SignaturesCronApp',
        'TruncatePartitionsCronApp',
        'UploadCrashReportJSONSchemaCronApp',
        'WeeklyReportsPartitionsCronApp',
    ]

    def test_dotted_path(self):
        # This generates an "InnerClassList" which has a list of tuples of the
        # form (class name, class). We verify we have the expected set here.
        jobs = jobs_converter('socorro.cron.crontabber_app.DEFAULT_JOBS')
        job_names = sorted([job_name for job_name, job_class in jobs.class_list])
        assert job_names == self.expected_job_names

    def test_jobs_spec(self):
        # This generates an "InnerClassList" which has a list of tuples of the
        # form (class name, class). We verify we have the expected set here.
        jobs = jobs_converter(DEFAULT_JOBS)
        job_names = sorted([job_name for job_name, job_class in jobs.class_list])
        assert job_names == self.expected_job_names
