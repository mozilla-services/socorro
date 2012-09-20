/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.apache.hadoop.hbase.rest.model;

import java.io.Serializable;

import javax.xml.bind.annotation.*;

@XmlRootElement(name="QueueString")
public class QueueStringModel implements Serializable {

	private static final long serialVersionUID = -3786103919288807294L;

	private String value;

	public QueueStringModel() {
	}

	public QueueStringModel(String value) {
		this.value = value;
	}

	@XmlAttribute
	public String getValue() {
		return value;
	}

	public void setValue(String value) {
		this.value = value;
	}

	/* (non-Javadoc)
	 * @see java.lang.Object#toString()
	 */
	@Override
	public String toString() {
		return value;
	}

}
