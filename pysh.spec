Summary:	PySH - a Python shell
Summary(pl):	PySH - pow³oka z osadzonym Pythonem
Name:		pysh
Version:	0.04
Release:	1
License:	BSD
Group:		Applications/Shells
Source0:	http://unixnaut.com/skills/Languages/python/%{name}.py
# NoSource0-md5:	75c7eeb4ee72168de2ac34f4c27fa8ec
URL:		http://unixnaut.com/skills/Languages/python/pysh.html
BuildRequires:	python-modules >= 2.2.1
BuildRequires:	rpm-pythonprov
BuildArch:	noarch
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
PySH is a Python shell. It works as a replacement for Bash. You can do
your normal shell things but using Python variables, functions,
conditions, etc. It functions as both a Python interpretter and shell,
depending on command context.

%description -l pl
PySH jest pow³ok± z osadzonym Pythonem, która mo¿e byæ u¿yta jako
zamiennik dla Basha. Umo¿liwia wykonywanie zwyczajowych operacji
udostêpnianych przez pow³oki po³±czonych z wykorzystaniem pythonowych
zmiennych, funkcji, warunków, itd.  Dzia³a zarówno jako interpreter
Pythona, jak równie¿ jako pow³oka, w zale¿no¶ci od kontekstu wywo³anej
komendy.

%prep

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT%{_bindir}

install %{SOURCE0} $RPM_BUILD_ROOT%{_bindir}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%attr(755,root,root) %{_bindir}/pysh.py
