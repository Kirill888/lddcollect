from lddcollect import dpkg_s


def test_dpkg_s():
    debs, missing = dpkg_s("/usr/bin/dpkg")
    assert len(missing) == 0
    assert debs == [("dpkg", "/usr/bin/dpkg")]

    no_such = "/no/such/file/fa61bffb9352"
    no_such2 = "/no/such/file2/fa61bffb9352"

    debs, missing = dpkg_s("/usr/bin/dpkg", no_such)
    assert debs == [("dpkg", "/usr/bin/dpkg")]
    assert missing == [no_such]

    debs, missing = dpkg_s(no_such, no_such2)
    assert len(debs) == 0
    assert missing == [no_such, no_such2]
