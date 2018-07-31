/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from 'react';
import ReactDOM from 'react-dom';

import ReportIndex from 'socorro/report-index';

const crashReportContainer = document.getElementById('crash-report-container');
const crashId = crashReportContainer.dataset.crashId;

ReactDOM.render(<ReportIndex crashId={crashId} />, crashReportContainer);
