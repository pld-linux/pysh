Summary:	PySH - a Python shell
Summary(pl):	PySH - pow�oka z osadzonym Pythonem
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
PySH jest pow�ok� z osadzonym Pythonem, kt�ra mo�e by� u�yta jako
zamiennik dla Basha. Umo�liwia wykonywanie zwyczajowych operacji
udost�pnianych przez pow�oki po��czonych z wykorzystaniem pythonowych
zmiennych, funkcji, warunk�w, itd.  Dzia�a zar�wno jako interpreter
Pythona, jak r�wnie� jako pow�oka, w zale�no�ci od kontekstu wywo�anej
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
