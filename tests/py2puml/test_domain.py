import unittest
from pathlib import Path

import tests.modules
import tests.modules.withabstract
import tests.modules.withnestednamespace
import tests.modules.withsubdomain
from tests.modules.withmethods.withmethods import Point
from tests.modules.withnestednamespace.withoutumlitemroot.withoutumlitemleaf import withoutumlitem
from tests.modules.withnestednamespace.withonlyonesubpackage.underground.roots import roots
from tests.modules.withnestednamespace.withonlyonesubpackage.underground import Soil
from tests.modules.withnestednamespace import branches
from py2puml.domain.umlclass import PythonPackage, PythonModule, PythonClass, UmlMethod, ClassAttribute, InstanceAttribute, Attribute, PackageType, ModuleImport


SRC_DIR = Path(__file__).parent.parent.parent
TESTS_DIR = SRC_DIR / 'tests'
MODULES_DIR = TESTS_DIR / 'modules'


class TestPythonClass(unittest.TestCase):

    def setUp(self) -> None:

        self.point_class = PythonClass(
            name='Point',
            fully_qualified_name='tests.modules.withmethods.withmethods.Point',
            attributes=[
                ClassAttribute(name='PI', _type='float'),
                ClassAttribute(name='origin'),
                InstanceAttribute(name='coordinates', _type='Coordinates'),
                InstanceAttribute(name='day_unit', _type='TimeUnit'),
                InstanceAttribute(name='hour_unit', _type='TimeUnit'),
                InstanceAttribute(name='time_resolution', _type='Tuple[str, TimeUnit]'),
                InstanceAttribute(name='x', _type='int'),
                InstanceAttribute(name='y', _type='Tuple[bool]')],
            methods=[
                UmlMethod(
                    name='from_values',
                    arguments={'x': 'int', 'y': 'str'},
                    is_static=True,
                    return_type='Point'),
                UmlMethod(
                    name='get_coordinates',
                    arguments={'self': None},
                    return_type='Tuple[float, str]'),
                UmlMethod(
                    name='__init__',
                    arguments={'self': None, 'x': 'int', 'y': 'Tuple[bool]'}),
                UmlMethod(
                    name='do_something',
                    arguments={'self': None, 'posarg_nohint': None, 'posarg_hint': 'str', 'posarg_default': None},
                    return_type='int')])

    def test_from_type(self):
        _class = PythonClass.from_type(Point)
        self.assertEqual('Point', _class.name)
        self.assertEqual('tests.modules.withmethods.withmethods.Point', _class.fully_qualified_name)

    def test_from_type_init_module(self):
        """ Test the from_type alternate constructor with a class initializes in a __init__ module """
        _class = PythonClass.from_type(Soil)
        expected_fqn = 'tests.modules.withnestednamespace.withonlyonesubpackage.underground.Soil'
        self.assertEqual(expected_fqn, _class.fully_qualified_name)

    def test_as_puml(self):
        expected_result = '''class tests.modules.withmethods.withmethods.Point {
  PI: float {static}
  origin {static}
  coordinates: Coordinates
  day_unit: TimeUnit
  hour_unit: TimeUnit
  time_resolution: Tuple[str, TimeUnit]
  x: int
  y: Tuple[bool]
  {static} Point from_values(int x, str y)
  Tuple[float, str] get_coordinates(self)
  __init__(self, int x, Tuple[bool] y)
  int do_something(self, posarg_nohint, str posarg_hint, posarg_default)
}\n'''

        actual_result = self.point_class.as_puml

        self.assertEqual(expected_result, actual_result)


class TestPythonModule(unittest.TestCase):

    def test_from_imported_module(self):
        module = PythonModule.from_imported_module(tests.modules.withabstract)
        self.assertEqual('withabstract', module.name)
        self.assertEqual('tests.modules.withabstract', module.fully_qualified_name)
        self.assertEqual(MODULES_DIR / 'withabstract.py', module.path)

    def test_visit(self):
        module = PythonModule(
            name='withconstructor',
            fully_qualified_name='tests.modules.withconstructor',
            path=MODULES_DIR / 'withconstructor.py'
        )
        module.visit()

        expected_class_names = ['Coordinates', 'Point']
        actual_class_names = [_class.name for _class in module.classes]

        self.assertCountEqual(expected_class_names, actual_class_names)  #FIXME: test more than classes name

    def test_visit_2(self):
        module = PythonModule(
            name='withmethods',
            fully_qualified_name='tests.modules.withmethods.withmethods',
            path=MODULES_DIR / 'withmethods' / 'withmethods.py'
        )
        module.visit()

        expected_class_names = ['Coordinates', 'Point']
        actual_class_names = [_class.name for _class in module.classes]

        self.assertCountEqual(expected_class_names, actual_class_names)  #FIXME: test more than classes name

    def test_visit_3(self):
        """ Test that the import statements are correctly processed """

        module = PythonModule(
            name='branch',
            fully_qualified_name='tests.modules.withnestednamespace.branches.branch',
            path=MODULES_DIR / 'withnestednamespace' / 'branches' / 'branch.py'
        )
        module.visit()
        self.assertEqual(5, len(module.imports))

    def test_has_classes(self):
        """ Test the has_classes property on a module containing two classes """
        module = PythonModule.from_imported_module(tests.modules.withmethods.withmethods)
        module.visit()
        self.assertTrue(module.has_classes)

    def test_has_classes_2(self):
        """ Test the has_classes property on a module containing one dataclass """
        module = PythonModule.from_imported_module(roots)
        module.visit()
        self.assertTrue(module.has_classes)

    def test_has_classes_3(self):
        """ Test the has_classes property on a module not containing any class """
        module = PythonModule.from_imported_module(withoutumlitem)
        module.visit()
        self.assertFalse(module.has_classes)


class TestPythonPackage(unittest.TestCase):

    def setUp(self) -> None:
        module1 = PythonModule(name='withmethods', fully_qualified_name='tests.modules.withmethods.withmethods', path=MODULES_DIR / 'withmethods' / 'withmethods.py')
        module2 = PythonModule(name='withinheritedmethods', fully_qualified_name='tests.modules.withmethods.withinheritedmethods', path=MODULES_DIR / 'withmethods' / 'withinheritedmethods.py')
        module1.visit()
        module2.visit()
        self.package = PythonPackage(path=MODULES_DIR / 'withmethods', name='withmethods', fully_qualified_name='tests.modules.withmethods')
        self.package.modules.append(module1)
        self.package.modules.append(module2)

    def test_from_imported_package(self):
        package = PythonPackage.from_imported_package(tests.modules)
        self.assertEqual(TESTS_DIR / 'modules', package.path)
        self.assertEqual('modules', package.name)
        self.assertEqual('tests.modules', package.fully_qualified_name)

    def test_has_sibling_root(self):
        """ Test has_sibling property on root package with modules only """
        self.assertFalse(self.package.has_sibling)

    def test_has_sibling(self):
        """ Test has_sibling property on package containing subpackages """
        root_package = PythonPackage(path=MODULES_DIR, name='root', fully_qualified_name='root')
        package1 = PythonPackage(path=MODULES_DIR, name='pkg1', fully_qualified_name='root.pkg1')
        package2 = PythonPackage(path=MODULES_DIR, name='pkg2', fully_qualified_name='root.pkg2')
        package1.parent_package = root_package
        package2.parent_package = root_package
        package11 = PythonPackage(path=MODULES_DIR / 'root', name='pkg11', fully_qualified_name='root.pkg1.pkg11')
        package11.parent_package = package1

        self.assertTrue(package1.has_sibling)
        self.assertTrue(package2.has_sibling)
        self.assertFalse(package11.has_sibling)

    def test_add_module(self):
        """ Test the _add_module method """
        package = PythonPackage(path=MODULES_DIR / 'withmethods', name='withmethods',
                                fully_qualified_name='tests.modules.withmethods')
        package.all_packages['tests.modules.withmethods'] = package
        package._add_module('tests.modules.withmethods.withmethods')
        module_obj = package.modules[0]

        self.assertEqual(1, len(package.modules))
        self.assertIn(module_obj, package.modules)
        self.assertTrue(module_obj.has_classes)
        self.assertEqual(package, module_obj.parent_package)

    def test_add_module_init(self):
        """ Test the _add_module method on a __init__ module containing class definition """
        package = PythonPackage(path=MODULES_DIR / 'withsubdomain', name='withsubdomain',
                                fully_qualified_name='tests.modules.withsubdomain')
        package.all_packages['tests.modules.withsubdomain'] = package
        package._add_module('tests.modules.withsubdomain.__init__')

        self.assertEqual(1, len(package.classes))
        self.assertEqual(1, len(package.modules))

    def test_add_subpackage(self):
        """ Test the _add_subpackage method """
        package = PythonPackage(path=MODULES_DIR, name='modules',
                                fully_qualified_name='tests.modules')
        package.all_packages['tests.modules'] = package
        subpackage = package._add_subpackage('tests.modules.withmethods')

        self.assertIsInstance(subpackage, PythonPackage)
        self.assertEqual(package, subpackage.parent_package)
        self.assertIn('withmethods', package.subpackages.keys())
        self.assertEqual(subpackage, package.subpackages['withmethods'])
        self.assertEqual(1, subpackage.depth)
        self.assertDictEqual({'tests.modules': package, 'tests.modules.withmethods': subpackage}, package.all_packages)

    def test_walk(self):
        """ Test the walk method on the tests.modules package and make sure the package and module are correctly
        hierarchized """

        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()

        self.assertEqual(9, len(package.modules))
        self.assertEqual(5, len(package.subpackages))
        self.assertEqual(PackageType.NAMESPACE, package._type)
        self.assertEqual(0, package.depth)

        package_withsubdomain = package.subpackages['withsubdomain']
        self.assertEqual(PackageType.REGULAR, package_withsubdomain._type)
        self.assertEqual(1, len(package_withsubdomain.modules))
        self.assertEqual(1, len(package_withsubdomain.subpackages))
        self.assertEqual(1, package_withsubdomain.depth)

        package_subdomain = package_withsubdomain.subpackages['subdomain']
        self.assertEqual(PackageType.REGULAR, package_subdomain._type)
        self.assertEqual(1, len(package_subdomain.modules))
        self.assertEqual(0, len(package_subdomain.subpackages))
        self.assertEqual(2, package_subdomain.depth)

        package_withmethods = package.subpackages['withmethods']
        self.assertEqual(PackageType.NAMESPACE, package_withmethods._type)
        self.assertEqual(2, len(package_withmethods.modules))
        self.assertEqual(0, len(package_withmethods.subpackages))
        self.assertEqual(1, package_withmethods.depth)

    def test_walk_nested_namespace(self):
        """ Test the walk method on the tests.modules.withnestednamespace package which contains both regular and namespace packages """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()

        self.assertEqual(PackageType.NAMESPACE, package._type)
        self.assertEqual(5, len(package.subpackages))
        self.assertEqual(1, len(package.modules))

        pkg_branches = package.subpackages['branches']
        self.assertEqual(PackageType.NAMESPACE, pkg_branches._type)
        self.assertEqual(1, len(pkg_branches.modules))
        self.assertEqual(0, len(pkg_branches.subpackages))

        pkg_nomoduleroot = package.subpackages['nomoduleroot']
        self.assertEqual(PackageType.REGULAR, pkg_nomoduleroot._type)
        self.assertEqual(0, len(pkg_nomoduleroot.modules))
        self.assertEqual(1, len(pkg_nomoduleroot.subpackages))

        self.assertEqual(PackageType.NAMESPACE, package.subpackages['trunks']._type)
        self.assertEqual(1, len(package.subpackages['trunks'].modules))
        self.assertEqual(0, len(package.subpackages['trunks'].subpackages))

        package_withonlyonesubpackage = package.subpackages['withonlyonesubpackage']
        self.assertEqual(PackageType.REGULAR, package_withonlyonesubpackage._type)
        self.assertEqual(0, len(package_withonlyonesubpackage.modules))
        self.assertEqual(1, len(package_withonlyonesubpackage.subpackages))

        pkg_underground = package_withonlyonesubpackage.subpackages['underground']
        self.assertEqual(PackageType.REGULAR, pkg_underground._type)
        self.assertEqual(1, len(pkg_underground.modules))
        self.assertEqual(1, len(pkg_underground.subpackages))

        pkg_roots = pkg_underground.subpackages['roots']
        self.assertEqual(PackageType.NAMESPACE, pkg_roots._type)
        self.assertEqual(1, len(pkg_roots.modules))
        self.assertEqual(0, len(pkg_roots.subpackages))

        package_withoutumlitemroot = package.subpackages['withoutumlitemroot']
        self.assertEqual(PackageType.REGULAR, package_withoutumlitemroot._type)
        self.assertEqual(0, len(package_withoutumlitemroot .modules))
        self.assertEqual(1, len(package_withoutumlitemroot .subpackages))

        package_withoutumlitemleaf = package_withoutumlitemroot.subpackages['withoutumlitemleaf']
        self.assertEqual(PackageType.NAMESPACE, package_withoutumlitemleaf._type)
        self.assertEqual(1, len(package_withoutumlitemleaf .modules))
        self.assertEqual(0, len(package_withoutumlitemleaf .subpackages))

    def test_resolve_relative_imports(self):
        """ Test resolve_relative_imports method """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        pkg_branches = package.subpackages['branches']
        module_branch = pkg_branches.modules[0]
        self.assertIsNone(module_branch.imports['OakLeaf'].fully_qualified_name)

        package.resolve_relative_imports()

        expected_value = 'tests.modules.withnestednamespace.nomoduleroot.modulechild.leaf'
        actual_value = module_branch.imports['OakLeaf'].fully_qualified_name

        self.assertEqual(expected_value, actual_value)

    def test_resolve_class_inheritance_1(self):
        """ Test resolve_class_inheritance method when the class and its base class are in the same module """
        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()
        package.resolve_relative_imports()
        package.resolve_class_inheritance()

        pkg_withnestednamespace = package.subpackages['withnestednamespace']
        pkg_branches = pkg_withnestednamespace.subpackages['branches']
        module_branch = pkg_branches.modules[0]
        class_oak_branch = module_branch.classes[1]

        expected_fully_qualified_name = 'tests.modules.withnestednamespace.branches.branch.Branch'
        actual_fully_qualified_name = class_oak_branch.base_classes['Branch'].fully_qualified_name
        self.assertEqual(expected_fully_qualified_name, actual_fully_qualified_name)

    def test_resolve_class_inheritance_2(self):
        """ Test resolve_class_inheritance method when the class and its base class are in different modules. Also tests
         that aliased import are correctly resolved (in this case 'CommonLeaf' is an alias of the 'CommownLeaf' class in
         the 'leaf' module """
        package = PythonPackage.from_imported_package(tests.modules)
        package.walk()
        package.resolve_relative_imports()
        package.resolve_class_inheritance()

        pkg_withnestednamespace = package.subpackages['withnestednamespace']
        pkg_branches = pkg_withnestednamespace.subpackages['branches']
        module_branch = pkg_branches.modules[0]
        class_birch_leaf = module_branch.classes[2]

        expected_fully_qualified_name = 'tests.modules.withnestednamespace.nomoduleroot.modulechild.leaf.CommownLeaf'
        actual_fully_qualified_name = class_birch_leaf.base_classes['CommonLeaf'].fully_qualified_name
        self.assertEqual(expected_fully_qualified_name, actual_fully_qualified_name)

    def test_find_all_classes_1(self):
        """ Test find_all_classes method on a package containing modules only """
        all_classes = self.package.find_all_classes()
        self.assertEqual(4, len(all_classes))

    def test_find_all_classes_2(self):
        """ Test find_all_classes method on a package containing subpackages """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        all_classes = package.find_all_classes()
        self.assertEqual(11, len(all_classes))

    def test_find_all_modules_1(self):
        """ Test find_all_classes method on a package containing modules only """
        all_modules = self.package.find_all_modules()
        self.assertEqual(2, len(all_modules))

    def test_find_all_modules_2(self):
        """ Test find_all_classes method on a package containing subpackages """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()

        all_modules = package.find_all_modules()
        self.assertEqual(7, len(all_modules))

    def test_find_all_modules_3(self):
        """ Test find_all_classes method on a package containing subpackages with the skip_empty flag turned on """
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()

        all_modules = package.find_all_modules(skip_empty=True)
        self.assertEqual(6, len(all_modules))

    def test_as_puml(self):
        package = PythonPackage.from_imported_package(tests.modules.withsubdomain)
        package.walk()

        expected_result = '''namespace tests.modules.withsubdomain {
  namespace withsubdomain {}
  namespace subdomain.insubdomain {}
}\n'''
        actual_result = package.as_puml
        print(actual_result)
        self.assertEqual(expected_result, actual_result)

    def test_as_puml_2(self):
        # FIXME: indentation problem must be fixed
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        expected_result = '''namespace tests.modules.withnestednamespace {
  namespace tree {}
  namespace branches.branch {}
  namespace nomoduleroot.modulechild.leaf {}
  namespace trunks.trunk {}
  namespace withonlyonesubpackage.underground {
    namespace roots.roots {}
  }
}\n'''
        actual_result = package.as_puml
        print(actual_result)
        self.assertEqual(expected_result, actual_result)


class TestClassAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.typed_attribute = ClassAttribute(name='PI', _type='float')
        self.untyped_attribute = ClassAttribute(name='origin')

    def test_constructor_typed(self):
        class_attribute = ClassAttribute(name='PI', _type='float')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, ClassAttribute)
        self.assertEqual('PI', class_attribute.name)
        self.assertEqual('float', class_attribute._type)

    def test_constructor_untyped(self):
        class_attribute = ClassAttribute(name='origin')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, ClassAttribute)
        self.assertEqual('origin', class_attribute.name)
        self.assertIsNone(class_attribute._type)

    def test_as_puml_typed(self):
        expected_result = 'PI: float {static}'
        actual_result = self.typed_attribute.as_puml
        self.assertEqual(expected_result, actual_result)

    def test_as_puml_untyped(self):
        expected_result = 'origin {static}'
        actual_result = self.untyped_attribute.as_puml
        self.assertEqual(expected_result, actual_result)


class TestInstanceAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.typed_attribute = InstanceAttribute(name='attribute1', _type='int')
        self.untyped_attribute = InstanceAttribute(name='attribute2')

    def test_constructor_typed(self):
        class_attribute = InstanceAttribute(name='attribute1', _type='int')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, InstanceAttribute)
        self.assertEqual('attribute1', class_attribute.name)
        self.assertEqual('int', class_attribute._type)

    def test_constructor_untyped(self):
        class_attribute = InstanceAttribute(name='attribute2')
        self.assertIsInstance(class_attribute, Attribute)
        self.assertIsInstance(class_attribute, InstanceAttribute)
        self.assertEqual('attribute2', class_attribute.name)
        self.assertIsNone(class_attribute._type)

    def test_as_puml_typed(self):
        expected_result = 'attribute1: int'
        actual_result = self.typed_attribute.as_puml
        self.assertEqual(expected_result, actual_result)

    def test_as_puml_untyped(self):
        expected_result = 'attribute2'
        actual_result = self.untyped_attribute.as_puml
        self.assertEqual(expected_result, actual_result)


class TestModuleImport(unittest.TestCase):

    def test_resolve_relative_import(self):
        """ Test the resolve_relative_import method with a 2-level relative import. The relative module qualified
        name passed as input 'nomoduleroot.modulechild.leaf' correspond in the Python module to the source code
        '..nomoduleroot.modulechild.leaf' """

        module_import = ModuleImport(
            module_name='nomoduleroot.modulechild.leaf',
            name='OakLeaf',
            alias=None,
            level=2
        )
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        branches_package = package.subpackages['branches']
        branch_module = branches_package.modules[0]

        expected_result = 'tests.modules.withnestednamespace.nomoduleroot.modulechild.leaf'
        module_import.resolve_relative_import(branch_module)

        self.assertEqual(expected_result, module_import.fully_qualified_name)

    def test_resolve_relative_import_2(self):
        """ Test the resolve_relative_import method with a 1-level relative import. The relative module qualified
        name passed as input 'trunks.trunk' correspond in the Python module to the source code
        '.trunkss.trunk' """

        module_import = ModuleImport(
            module_name='trunks.trunk',
            name='Trunk',
            alias=None,
            level=1
        )
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        tree_module = package.modules[0]

        expected_result = 'tests.modules.withnestednamespace.trunks.trunk'
        module_import.resolve_relative_import(tree_module)

        self.assertEqual(expected_result, module_import.fully_qualified_name)

    def test_resolve_relative_import_3(self):
        """ Test the resolve_relative_import method raises and error when import cannot be resolved due to parent missing in module hierarchy"""

        module_import = ModuleImport(
            module_name='trunks.trunk',
            name='Trunk',
            alias=None,
            level=3
        )
        package = PythonPackage.from_imported_package(tests.modules.withnestednamespace)
        package.walk()
        tree_module = package.modules[0]

        with self.assertRaises(Exception):
            module_import.resolve_relative_import(tree_module)

