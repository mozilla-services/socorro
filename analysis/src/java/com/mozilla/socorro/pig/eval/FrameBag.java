/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package com.mozilla.socorro.pig.eval;

import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.pig.EvalFunc;
import org.apache.pig.data.BagFactory;
import org.apache.pig.data.DataBag;
import org.apache.pig.data.Tuple;
import org.apache.pig.data.TupleFactory;

public class FrameBag extends EvalFunc<DataBag> {

	private static final Pattern framePattern = Pattern.compile("^([0-9]+)\\|([0-9]+)");
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
			Matcher m = framePattern.matcher(dumpline);
			if (m.find()) {
				// TODO: validate??
				// frame_group, frame_idx, module, method, src_file, number??, hex??
				Tuple t = tupleFactory.newTuple();
				String[] splits = pipePattern.split(dumpline, -1);
				for (int i=0; i < splits.length; i++) {
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
