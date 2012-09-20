/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.pig.eval;

import java.io.IOException;
import java.util.regex.Pattern;

import org.apache.pig.EvalFunc;
import org.apache.pig.data.BagFactory;
import org.apache.pig.data.DataBag;
import org.apache.pig.data.Tuple;
import org.apache.pig.data.TupleFactory;

public class ModuleBag extends EvalFunc<DataBag> {

	private static final String MODULE_PATTERN = "Module|";

	private static final Pattern newlinePattern = Pattern.compile("\n");
	private static final Pattern pipePattern = Pattern.compile("\\|");
	private static final BagFactory bagFactory = BagFactory.getInstance();
	private static final TupleFactory tupleFactory = TupleFactory.getInstance();

	public DataBag exec(Tuple input) throws IOException {
		if (input == null || input.size() == 0) {
			return null;
		}

		reporter.progress();
		DataBag db = bagFactory.newDefaultBag();
		for (String dumpline : newlinePattern.split((String)input.get(0))) {
			if (dumpline.startsWith(MODULE_PATTERN)) {
				// TODO: validate??
				// module_str, libname, version, pdb, checksum, addrstart, addrend, unknown
				Tuple t = tupleFactory.newTuple();
				String[] splits = pipePattern.split(dumpline, -1);
				for (int i=1; i < splits.length; i++) {
					t.append(splits[i]);
				}
				if (t.size() > 0) {
					db.add(t);
				}
			}
		}

		return db;
	}
}
