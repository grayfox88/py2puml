from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass, field
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module
from ast import parse
from abc import ABC, abstractmethod
from enum import Enum
from setuptools import find_namespace_packages

from py2puml.domain.umlitem import UmlItem
import py2puml.parsing.astvisitors as astvisitors


class PackageType(Enum):
    REGULAR = 1
    NAMESPACE = 2


@dataclass
class UmlAttribute:
    name: str
    type: str
    static: bool


@dataclass
class UmlMethod:
    name: str
    arguments: Dict = field(default_factory=dict)
    is_static: bool = False
    is_class: bool = False
    return_type: str = None

    @property
    def as_puml(self):
        items = []
        if self.is_static:
            items.append('{static}')
        if self.return_type:
            items.append(self.return_type)
        items.append(f'{self.name}({self.signature})')
        return ' '.join(items)

    @property
    def signature(self):
        if self.arguments:
            return ', '.join([f'{arg_type} {arg_name}' if arg_type else f'{arg_name}' for arg_name, arg_type in
                              self.arguments.items()])
        return ''


@dataclass
class UmlClass(UmlItem):
    attributes: List[UmlAttribute]
    methods: List[UmlMethod]
    is_abstract: bool = False


@dataclass
class PythonModule:
    """ Class that represent a Python module with its classes.

        Basic instantiation of objects is easily done with the 'from_imported_module' constructor method.

        Attributes:
            path (Path): path to the Python module file
            name (str): name of the Python module
            fully_qualified_name (str): fully qualified name of the Python module
            classes List[PythonModule]: list of classes in the module """
    name: str
    fully_qualified_name: str
    path: Path
    classes: List[PythonClass] = field(default_factory=list)
    imports: Dict[str, ModuleImport] = field(default_factory=dict)
    _parent_package: PythonPackage = None

    @classmethod
    def from_imported_module(cls, module_obj):
        """ Alternate constructor method that instantiate a PythonModule object from the corresponding imported module.

        Args:
            module_obj (module): imported module from e.g. the 'import' statement or importlib.import_module()

        Returns:
            An instantiated PythonModule object.
        """
        name = module_obj.__name__.split('.')[-1]
        fully_qualified_name = module_obj.__name__
        path = Path(module_obj.__file__)
        return PythonModule(name=name, fully_qualified_name=fully_qualified_name, path=path)

    @property
    def has_classes(self):
        return len(self.classes) > 0

    @property
    def parent_package(self) -> PythonPackage:
        return self._parent_package

    @parent_package.setter
    def parent_package(self, value: PythonPackage) -> None:
        self._parent_package = value
        value.modules.append(self)

    def visit(self):
        """ Visit AST node corresponding to the module in order to find classes. Import statement are also defined by
         this method and stored in a dictionary for faster look-up later. The fully_qualified_name property of
         ModuleImport objects is not set at this stage. It will be done by the resolve_relative_imports method once the
         packages hierarchy is fully-defined."""

        with open(self.path, 'r') as fref:
            content = fref.read()

        ast = parse(content, filename=str(self.path))
        visitor = astvisitors.ModuleVisitor(self.fully_qualified_name)
        visitor.visit(ast)

        for _class in visitor.classes:
            _class.module = self
            self.classes.append(_class)

        for module_import in visitor.module_imports:
            if module_import.alias:
                self.imports[module_import.alias] = module_import
            else:
                self.imports[module_import.name] = module_import

    def __contains__(self, class_name):
        return class_name in [_class.name for _class in self.classes]

    def find_class_by_name(self, class_name):
        """ Find a class in a module by its name and return the corresponding PythonClass instance.

        Args:
            class_name (str): name of the class to look for

        Returns:
            An instance of PythonClass if found, otherwise returns None """

        for _class in self.classes:
            if class_name == _class.name:
                return _class
        return None

    @property
    def parent_fully_qualified_name(self):
        return '.'.join(self.fully_qualified_name.split('.')[:-1])


@dataclass
class PythonPackage:
    """ Class that represent a regular Python package with its subpackages and modules.

    Basic instantiation of objects is easily done with the 'from_imported_package' constructor method. To search
    recursively for subpackages and modules, use the 'walk' method.

    Attributes:
        path (Path): path to the Python package folder
        name (str): name of the Python package
        fully_qualified_name (str): fully qualified name of the Python package
        depth (int): package depth level relative to the root package. Root package has level 0.
        modules (List[PythonModule]): list of modules found in the package
        subpackages (Dict[str, PythonPackage]): dictionary of subpackages found in the package"""
    path: Path
    name: str
    fully_qualified_name: str
    depth: int = 0
    _type: PackageType = PackageType.REGULAR
    modules: List[PythonModule] = field(default_factory=list)
    subpackages: Dict[str, PythonPackage] = field(default_factory=dict)
    _parent_package: PythonPackage = None
    all_packages: Dict[str, PythonPackage] = field(default_factory=dict)

    @property
    def parent_package(self) -> PythonPackage:
        return self._parent_package

    @parent_package.setter
    def parent_package(self, value: PythonPackage) -> None:
        self._parent_package = value
        value.subpackages[self.name] = self

    @classmethod
    def from_imported_package(cls, package_obj):
        """ Alternate constructor method that instantiate a PythonPackage object from the corresponding imported
        package.

        Args:
            package_obj (module): imported package from e.g. the 'import' statement or the importlib.import_module()

        Returns:
            A partially instantiated PythonPackage object. To fully instantiate it, proceed by running the 'walk' method
        """
        if isinstance(package_obj.__path__, list):
            path = Path(package_obj.__path__[0])
        else:
            path = Path(package_obj.__path__._path[0])
        name = package_obj.__name__.split('.')[-1]
        fully_qualified_name = package_obj.__name__

        init_filepath = path / '__init__.py'
        if init_filepath.is_file():
            _type = PackageType.REGULAR
        else:
            _type = PackageType.NAMESPACE

        return PythonPackage(path=path, name=name, fully_qualified_name=fully_qualified_name, depth=0, _type=_type)

    def _add_module(self, module_fully_qualified_name: str, skip_empty: bool = False) -> None:
        """ Add a new module to a package from its name.

        This method imports first the module and instantiate a PythonModule object from it. Classes in this
        PythonModule are resolved by visiting the AST corresponding to this module. This method also establish
        parent-child relationship between package and module.

        Args:
            module_fully_qualified_name (str): fully qualified module name
            skip_empty (bool): if set to True skip adding module if it has no classes """

        imported_module = import_module(module_fully_qualified_name)
        module = PythonModule.from_imported_module(imported_module)
        module.visit()

        if not skip_empty or module.has_classes:
            parent_package = self.all_packages[module.parent_fully_qualified_name]
            module.parent_package = parent_package

    def _add_subpackage(self, subpackage_fully_qualified_name: str) -> PythonPackage:
        """ Add a new subpackage to a package from its name.

        This method imports first the module and instantiate a PythonModule object from it. Classes in this
        PythonModule are resolved by visiting the AST corresponding to this module. This method also establish
        parent-child relationship between package and subpackage and define the depth of the subpackage (0 corresponds
        to the root package).

        Args:
            subpackage_fully_qualified_name (str): fully qualified package name

        Returns;
            The subpackage itself """

        imported_package = import_module(subpackage_fully_qualified_name)
        subpackage = PythonPackage.from_imported_package(imported_package)

        self.all_packages[subpackage.fully_qualified_name] = subpackage
        parent_package = self.all_packages[subpackage.parent_fully_qualified_name]
        subpackage.depth = parent_package.depth + 1
        subpackage.parent_package = parent_package

        return subpackage

    def walk(self):
        """
        Find subpackages and modules recursively

        Uses the setuptools.find_namespace_packages method to search recursively for regular and namespace
        subpackages of a given root package (the instance 'self' in this case). Create instances of PythonPackage
        object when a subpackage is found and add it as a subpackage while preserving hierarchy (see implementation
        in method _add_subpackage ).

        Since setuptools.find_namespace_packages flattens the package hierarchy, the instance attribute
        'all_packages' is used to store all packages found (including the top-level package). New packages found are
        appended to the 'subpackages' attribute of the parent package.

        Use the pkgutils.iter_modules() method to find modules in a package. When a module is found the method
        _add_module() will create a PythonModule instance, visit it  and add this object as a module of the
        corresponding PythonPackage object (see attribute 'modules'). For regular packages, the ``__init__`` module
        is visited and if class(es) is/are found, this module will also be added to the PythonPackage.modules
        attribute with the _add_module method.

        Note:
            Found subpackages and modules are imported.
        """
        # FIXME: crash when path passed as string and ending with '/'

        self.all_packages[self.fully_qualified_name] = self

        namespace_packages_names = find_namespace_packages(str(self.path))
        namespace_packages_names.insert(0, None)

        for namespace_package_name in namespace_packages_names:
            if namespace_package_name:
                package = self._add_subpackage(f'{self.fully_qualified_name}.{namespace_package_name}')
            else:
                package = self

            if package._type == PackageType.REGULAR:
                self._add_module(f'{package.fully_qualified_name}.__init__', skip_empty=True)

            for _, name, is_pkg in iter_modules(path=[package.path]):
                if not is_pkg:
                    self._add_module(f'{package.fully_qualified_name}.{name}')

    def find_all_classes(self) -> List[PythonClass]:
        """ Find all classes in a given package declared in their modules, by looking recursively into subpackages.

        Returns:
            List of PythonClass objects """
        classes = []
        for module in self.modules:
            classes.extend(module.classes)
        for subpackage in self.subpackages.values():
            classes.extend(subpackage.find_all_classes())
        return classes

    def find_all_modules(self, skip_empty: bool = False) -> List[PythonModule]:
        """ Find all modules in a given package, looking recursively into subpackages. Modules not containing any
        class can be ignored by passing the optional parameter 'skip_empty' as True.

        Args:
            skip_empty (bool): exclude modules not containing any class

        Returns:
            List of PythonModule objects """
        modules = []
        for module in self.modules:

            if not skip_empty or module.has_classes:
                modules.append(module)
        for subpackage in self.subpackages.values():
            modules.extend(subpackage.find_all_modules(skip_empty=skip_empty))
        return modules

    def resolve_relative_imports(self):
        """ Resolve relative import for all modules contained in a package and its subpackage.

        This method calls recursively the PythonModule.resolve_relative_import and all modules and subpackages
        modules """

        for module in self.modules:
            for module_import in module.imports.values():
                if module_import.is_relative:
                    module_import.resolve_relative_import(module)

        for subpackage in self.subpackages.values():
            subpackage.resolve_relative_imports()

    @property
    def parent_fully_qualified_name(self):
        return '.'.join(self.fully_qualified_name.split('.')[:-1])

    @property
    def has_sibling(self):
        if self.parent_package:
            return len(self.parent_package.subpackages) > 1
        return False

    @property
    def as_puml(self) -> str:
        """ Returns a plantUML representation of the package that will be used in the
        'namespace' declaration of the .puml file.

        Returns:
            PlantUML representation of package"""
        # FIXME: small issue with indentation
        # FIXME: should be removed according to Issue#53 ?!?!
        modules = [module for module in self.modules if module.has_classes]

        if self.depth == 0:
            puml_str = f'namespace {self.fully_qualified_name}'
        else:
            if self.has_sibling or self.parent_package.modules:
                indentation = self.depth * '  '
                puml_str = f'\n{indentation}namespace {self.name}'
            else:
                puml_str = f'.{self.name}'

        if len(self.subpackages) + len(modules) > 1:
            puml_str = puml_str + ' {'
            indentation = (self.depth + 1) * '  '
            for module in modules:
                puml_str = puml_str + f'\n{indentation}namespace {module.name} {{}}'

            for subpackage in self.subpackages.values():
                puml_str = puml_str + subpackage.as_puml

        elif len(modules) == 1:
            puml_str = puml_str + f'.{modules[0].name} {{}}'

        elif len(self.subpackages):
            subpackage = next(iter(self.subpackages.values()))
            puml_str = puml_str + subpackage.as_puml

        else:
            puml_str = ''

        if len(self.subpackages) + len(modules) > 1:
            indentation = self.depth * '  '
            puml_str = puml_str + f'\n{indentation}}}\n'

        if self.depth == 0:
            lines = puml_str.split('\n')
            clean_lines = [line for line in lines if (line.endswith('{') or line.endswith('}')) and '__init__' not in line]
            puml_str = '\n'.join(clean_lines)

        return puml_str


@dataclass
class PythonClass:
    """ Class that represents a Python class

    Args:
        name
        fully_qualified_name
        attributes
        methods
        base_classes (dict): dictionary which key is the partially qualified name of a base class and value is the
        corresponding base class object that the class inherits from.
        module (PythonModule): the Python module that the class belongs to
    """
    name: str
    fully_qualified_name: str
    attributes: List = field(default_factory=list)
    methods: List = field(default_factory=list)
    module: PythonModule = None

    @classmethod
    def from_type(cls, class_type):
        name = class_type.__name__
        fully_qualified_name = '.'.join([class_type.__module__, name])
        return PythonClass(name=name, fully_qualified_name=fully_qualified_name)

    @property
    def as_puml(self):
        lines = [f'class {self.fully_qualified_name} {{']
        for attribute in self.attributes:
            lines.append(f'  {attribute.as_puml}')
        for method in self.methods:
            lines.append(f'  {method.as_puml}')
        lines.append('}')

        return '\n'.join(lines)


class Attribute(ABC):

    def __init__(self, name, _type=None):
        self.name = name
        self._type = _type

    def __eq__(self, other):
        if isinstance(other, Attribute):
            return self.name == other.name and self._type == other._type
        return False

    def __ne__(self, other):
        return not self == other

    @property
    @abstractmethod
    def as_puml(self):
        pass


class ClassAttribute(Attribute):

    @property
    def as_puml(self):
        if self._type:
            return f'{self.name}: {self._type} {{static}}'
        else:
            return f'{self.name} {{static}}'


class InstanceAttribute(Attribute):

    @property
    def as_puml(self):
        if self._type:
            return f'{self.name}: {self._type}'
        else:
            return f'{self.name}'


class ClassDiagram:
    INDENT = 2

    def __init__(self, package: PythonPackage):
        self.package: PythonPackage = package
        self.classes: List[PythonClass] = package.find_all_classes()
        self.relationships = []

    def generate(self):
        yield self.header
        yield self.package.as_puml
        for _class in self.classes:
            yield _class.as_puml
        yield self.footer

    @property
    def header(self):
        return f'@startuml {self.package.fully_qualified_name}\n'

    @property
    def footer(self):
        return 'footer Generated by //py2puml//\n@enduml\n'


@dataclass
class ModuleImport:
    """ fully_qualified_name is set only once all modules and packages have been instantiated and their hierarchy
    established (with the PythonPackage.walk method) by running the  PythonModule.resolve_relative_import()

    Args:
        module_name (str): qualified module name to be resolved. It should not be prepended by any '.' character.
        level (int): how many level relative to the current module (self) should the module_name be resolved. """
    module_name: str
    name: str
    alias: str = None
    level: int = 0
    fully_qualified_name: str = None

    def resolve_relative_import(self, module: PythonModule) -> None:
        """ This method resolves relative qualified module names to a fully qualified module name.

        Args:
            module (PythonModule): module containing the import statement """

        parent = module
        while self.level > 0:
            if not parent.parent_package:
                raise(Exception(f'Could not resolve relative import from {self.module_name} since package {module.fully_qualified_name} has no parent.'))
            parent = parent.parent_package
            self.level -= 1
        self.fully_qualified_name = f'{parent.fully_qualified_name}.{self.module_name}'

    @property
    def is_relative(self):
        return self.level > 0
