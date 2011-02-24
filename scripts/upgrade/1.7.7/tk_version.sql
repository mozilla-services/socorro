CREATE LANGUAGE plperl;

BEGIN;

CREATE OR REPLACE FUNCTION tokenize_version(
    version TEXT,
	OUT s1n1 INT,
	OUT s1s1 TEXT,
	OUT s1n2 INT,
	OUT s1s2 TEXT,
	OUT s2n1 INT,
	OUT s2s1 TEXT,
	OUT s2n2 INT,
	OUT s2s2 TEXT,
	OUT s3n1 INT,
	OUT s3s1 TEXT,
	OUT s3n2 INT,
	OUT s3s2 TEXT,
	OUT ext TEXT
) LANGUAGE plperl AS $$
    my $version = shift;
    my @parts = split /[.]/ => $version;
    my $extra;
    if (@parts > 3) {
        $extra = join '.', @parts[3..$#parts];
        @parts = @parts[0..2];
    }

    my @tokens;
    for my $part (@parts) {
        die "$version is not a valid toolkit version" unless $part =~ qr{\A
            ([-]?\d+)                    # number-a
            (?:
                ([-_a-zA-Z]+(?=-|\d|\z)) # string-b
                (?:
                    (-?\d+)              # number-c
                    (?:
                        ([^-*+\s]+)      # string-d
                    |\z)
                |\z)
            |\z)
        \z}x;
        push @tokens, $1, $2, $3, $4;
    }

    die "$version is not a valid toolkit version" unless @tokens;
    my @cols = qw(s1n1 s1s1 s1n2 s1s2 s2n1 s2s1 s2n2 s2s2 s3n1 s3s1 s3n2 s3s2 ext);
    return { ext => $extra, map { $cols[$_] => $tokens[$_] } 0..11 }
$$;

SELECT * FROM tokenize_version('3');
SELECT * FROM tokenize_version('3.6');
SELECT * FROM tokenize_version('3.6.10pre');
SELECT * FROM tokenize_version('3.6.10plugin1');
SELECT * FROM tokenize_version('4pre.14a');
SELECT * FROM tokenize_version('1.3b.4a4bscone.4.23.34.bbq.wtf');
SELECT * FROM tokenize_version('0.0.0');

ROLLBACK;
