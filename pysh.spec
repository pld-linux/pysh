Summary:	PySH - a Python shell
Summary(pl.UTF-8):	PySH - powłoka z osadzonym Pythonem
Name:		pysh
Version:	0.04
Release:	1
License:	BSD
Group:		Applications/Shells
Source0:	http://unixnaut.com/skills/Languages/python/%{name}.py
# NoSource0-md5:	75c7eeb4ee72168de2ac34f4c27fa8ec
URL:		http://unixnaut.com/skills/Languages/python/pysh.html
BuildRequires:	python-modules >= 2.2.1
BuildArch:	noarch
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
PySH is a Python shell. It works as a replacement for Bash. You can do
your normal shell things but using Python variables, functions,
conditions, etc. It functions as both a Python interpretter and shell,
depending on command context.

%description -l pl.UTF-8
PySH jest powłoką z osadzonym Pythonem, która może być użyta jako
zamiennik dla Basha. Umożliwia wykonywanie zwyczajowych operacji
udostępnianych przez powłoki połączonych z wykorzystaniem pythonowych
zmiennych, funkcji, warunków, itd.  Działa zarówno jako interpreter
Pythona, jak również jako powłoka, w zależności od kontekstu wywołanej
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
